using System.Diagnostics;
using System.Text.Json;
using Velomux.Desktop.ViewModels;

namespace Velomux.Desktop.Services;

/// <summary>
/// Bounded, real FFmpeg extraction pilot. Source and existing outputs remain intact.
/// ffprobe must recognize audio before the staged result is published.
/// </summary>
public static class AudioConversionService
{
    public static async Task<string> ExtractAsync(
        string source, string destination, AudioOutputFormat format, CancellationToken token)
    {
        if (!File.Exists(source) || new FileInfo(source).Length == 0)
            throw new InvalidDataException("The source is missing or empty.");
        if (string.IsNullOrWhiteSpace(destination))
            throw new ArgumentException("Choose an output folder.", nameof(destination));

        Directory.CreateDirectory(destination);
        string ext = format == AudioOutputFormat.M4a ? ".m4a" : ".mp3";
        string stem = Path.GetFileNameWithoutExtension(source);
        string output = Path.Combine(destination, stem + " (Velomux)" + ext);
        string staged = Path.Combine(destination,
            "." + stem + ".velomux-stage-" + Guid.NewGuid().ToString("N") + ext);

        try
        {
            var p = NewProcess(FindExecutable("ffmpeg"));
            Add(p, "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
                "-i", source, "-map", "0:a:0", "-vn", "-map_metadata", "0",
                "-c:a", format == AudioOutputFormat.M4a ? "aac" : "libmp3lame",
                "-b:a", "192k", staged);
            await RunProcessAsync(p, token);
            if (!File.Exists(staged) || new FileInfo(staged).Length == 0)
                throw new InvalidDataException("FFmpeg did not create a nonempty audio file.");

            var check = NewProcess(FindExecutable("ffprobe"));
            check.RedirectStandardOutput = true;
            Add(check, "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_type", "-of", "json", staged);
            var outputText = await RunProcessAsync(check, token);
            using var json = JsonDocument.Parse(outputText);
            if (!json.RootElement.TryGetProperty("streams", out var streams)
                || streams.GetArrayLength() == 0)
                throw new InvalidDataException("ffprobe found no readable audio stream.");

            // A new numbered filename is safer than changing a preexisting
            // successful result. Publishing is atomic within one directory.
            for (int index = 2; ; index++)
            {
                token.ThrowIfCancellationRequested();
                try
                {
                    File.Move(staged, output, overwrite: false);
                    return output;
                }
                catch (IOException) when (File.Exists(output))
                {
                    output = Path.Combine(destination, stem + " (Velomux " + index + ")" + ext);
                }
            }
        }
        finally
        {
            if (File.Exists(staged))
                try { File.Delete(staged); } catch (IOException) { }
        }
    }

    private static ProcessStartInfo NewProcess(string executable) => new(executable)
    {
        UseShellExecute = false,
        CreateNoWindow = true,
        RedirectStandardError = true,
    };

    private static void Add(ProcessStartInfo p, params string[] args)
    {
        foreach (var item in args) p.ArgumentList.Add(item);
    }

    private static async Task<string> RunProcessAsync(ProcessStartInfo psi, CancellationToken token)
    {
        using var process = Process.Start(psi)
            ?? throw new IOException("Media processing executable could not start.");
        using var cancel = token.Register(() =>
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
            catch (InvalidOperationException) { }
        });
        var errorTask = process.StandardError.ReadToEndAsync();
        var outputTask = psi.RedirectStandardOutput
            ? process.StandardOutput.ReadToEndAsync()
            : Task.FromResult(string.Empty);
        await process.WaitForExitAsync(token);
        var error = await errorTask;
        var output = await outputTask;
        if (process.ExitCode != 0)
            throw new InvalidDataException(
                "FFmpeg/ffprobe returned " + process.ExitCode + ": " +
                (error.Length > 1200 ? error[^1200..] : error));
        return output;
    }

    private static string FindExecutable(string program)
    {
        string name = program + (OperatingSystem.IsWindows() ? ".exe" : "");
        foreach (string directory in new[]
        {
            AppContext.BaseDirectory,
            Path.Combine(AppContext.BaseDirectory, "ffmpeg"),
            Path.Combine(AppContext.BaseDirectory, "vendor", "ffmpeg", "bin"),
        })
        {
            string full = Path.Combine(directory, name);
            if (File.Exists(full)) return full;
        }
        // The engineering build permits a developer PATH. End-user installers
        // must provide and validate bundled FFmpeg/ffprobe instead.
        return name;
    }
}
