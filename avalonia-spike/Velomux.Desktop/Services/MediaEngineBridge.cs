using System.Diagnostics;
using System.Text.Json;
using Velomux.Desktop.ViewModels;

namespace Velomux.Desktop.Services;

public sealed record EngineProgress(double Percent, string Detail);
public sealed record EngineResult(string Status, string Output, string Detail);

/// <summary>
/// Avalonia talks to the original frozen, validated Velomux engine using a
/// line-oriented JSON protocol. No shell execution or interpreter on the PC.
/// </summary>
public static class MediaEngineBridge
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };
    private static string EngineExe
    {
        get
        {
            string path = Path.Combine(AppContext.BaseDirectory,
                "backend", "Velomux.Engine", "Velomux.Engine.exe");
            if (File.Exists(path)) return path;
            if (OperatingSystem.IsWindows())
                throw new FileNotFoundException("Bundled Velomux media engine is missing.", path);
            // Linux is supported for source development, not distribution.
            throw new FileNotFoundException("Frozen media engine is a Windows-only component.", path);
        }
    }
    private static ProcessStartInfo Create(string action)
    {
        var psi = new ProcessStartInfo(EngineExe)
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            WorkingDirectory = AppContext.BaseDirectory,
        };
        psi.ArgumentList.Add(action);
        return psi;
    }

    private static async Task<JsonDocument> SingleEventAsync(
        string action, object? request, CancellationToken token = default)
    {
        using var process = Process.Start(Create(action))
            ?? throw new IOException("Bundled media engine failed to start.");
        if (request != null)
        {
            await process.StandardInput.WriteLineAsync(JsonSerializer.Serialize(request));
        }
        process.StandardInput.Close();
        using var kill = token.Register(() =>
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
            catch (InvalidOperationException) { }
        });
        var outputTask = process.StandardOutput.ReadToEndAsync(token);
        var errorTask = process.StandardError.ReadToEndAsync(token);
        await process.WaitForExitAsync(token);
        string output = await outputTask;
        string error = await errorTask;
        if (string.IsNullOrWhiteSpace(output))
            throw new IOException("Engine produced no JSON response. " + Clip(error));
        string? last = output.Split('\n', StringSplitOptions.RemoveEmptyEntries).LastOrDefault();
        if (last == null) throw new InvalidDataException("The engine response was empty.");
        JsonDocument result = JsonDocument.Parse(last);
        if (process.ExitCode != 0 || result.RootElement.GetProperty("event").GetString() == "error")
        {
            string msg = result.RootElement.TryGetProperty("detail", out var d)
                ? d.GetString() ?? "" : error;
            result.Dispose();
            throw new InvalidDataException("Media engine error: " + Clip(msg));
        }
        return result;
    }

    private static string Clip(string value) => value.Length > 1600 ? value[^1600..] : value;

    public static async Task<CatalogOption> LoadCatalogAsync(CancellationToken token = default)
    {
        using var answer = await SingleEventAsync("--catalog", null, token);
        var result = answer.RootElement.Deserialize<CatalogOption>(JsonOptions);
        return result ?? throw new InvalidDataException("The engine returned no preset catalog.");
    }

    public static async Task<string> DescribeAsync(string source, CancellationToken token = default)
    {
        using var answer = await SingleEventAsync("--describe", new { source }, token);
        return answer.RootElement.GetProperty("detail").GetString() ?? "";
    }

    public static async Task<EngineResult> ConvertAsync(
        string source, string destination, string preset, object options,
        IProgress<EngineProgress>? progress, CancellationToken token)
    {
        using var process = Process.Start(Create("--convert"))
            ?? throw new IOException("Bundled media engine failed to start.");
        bool cancellationRequested = false;
        using var cancel = token.Register(() =>
        {
            cancellationRequested = true;
            try
            {
                if (!process.HasExited)
                {
                    process.StandardInput.WriteLine("CANCEL");
                    process.StandardInput.Flush();
                }
            }
            catch (IOException) { }
            catch (InvalidOperationException) { }
            catch (ObjectDisposedException) { }
        });
        await process.StandardInput.WriteLineAsync(JsonSerializer.Serialize(
            new { source, destination, preset, options }));
        await process.StandardInput.FlushAsync();
        // Keep stdin open to support an orderly CANCEL from the GUI.
        Task<string> stderrTask = process.StandardError.ReadToEndAsync();
        EngineResult? answer = null;
        try
        {
            string? line;
            while ((line = await process.StandardOutput.ReadLineAsync()) != null)
            {
                using var evt = JsonDocument.Parse(line);
                var root = evt.RootElement;
                string kind = root.GetProperty("event").GetString() ?? "";
                if (kind == "progress")
                {
                    double percentage = root.TryGetProperty("percent", out var n) ? n.GetDouble() : 0;
                    string detail = root.TryGetProperty("detail", out var d) ? d.GetString() ?? "" : "";
                    progress?.Report(new EngineProgress(percentage, detail));
                }
                else if (kind == "result")
                {
                    answer = new EngineResult(
                        root.GetProperty("status").GetString() ?? "failed",
                        root.TryGetProperty("output", out var o) ? o.GetString() ?? "" : "",
                        root.TryGetProperty("detail", out var d) ? d.GetString() ?? "" : "");
                }
                else if (kind == "error")
                {
                    answer = new EngineResult("failed", "",
                        root.TryGetProperty("detail", out var d) ? d.GetString() ?? "" : "Engine error");
                }
            }
            await process.WaitForExitAsync();
            string stderr = await stderrTask;
            if (answer == null)
            {
                if (cancellationRequested || token.IsCancellationRequested)
                    return new EngineResult("cancelled", "", "Conversion cancelled.");
                throw new IOException("Media engine produced no result. " + Clip(stderr));
            }
            if (process.ExitCode != 0 && answer.Status == "done")
                throw new IOException("Engine exited abnormally after reporting success.");
            return answer;
        }
        finally
        {
            try { process.StandardInput.Close(); } catch (IOException) { }
            if (!process.HasExited)
            {
                try { process.Kill(entireProcessTree: true); }
                catch (InvalidOperationException) { }
            }
        }
    }
}
