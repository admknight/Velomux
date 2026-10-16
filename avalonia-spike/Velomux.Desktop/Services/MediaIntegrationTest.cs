using System.Diagnostics;
using System.Globalization;
using System.Security.Cryptography;
using Velomux.Desktop.ViewModels;

namespace Velomux.Desktop.Services;

/// <summary>
/// Real conversion regression executed under GitHub Actions on Linux.
/// Uses a 7-second video with only 2 seconds of audio (the old Qt failure case).
/// </summary>
internal static class MediaIntegrationTest
{
    public static async Task RunAsync()
    {
        string root = Path.Combine(Path.GetTempPath(),
            "Velomux Avalonia audio test " + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            string source = Path.Combine(root, new string('A', 72) + " Jhankar 音楽 🎵.mp4");
            await RunToolAsync("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-t", "7", "-i", "color=c=blue:s=160x120:r=12",
                "-f", "lavfi", "-t", "2", "-i", "sine=frequency=440:sample_rate=44100",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "96k", source);

            byte[] sourceHash = SHA256.HashData(await File.ReadAllBytesAsync(source));
            string folder = Path.Combine(root, "Converted");
            string m4a = await AudioConversionService.ExtractAsync(
                source, folder, AudioOutputFormat.M4a, CancellationToken.None);
            if (!File.Exists(m4a) || new FileInfo(m4a).Length < 1000)
                throw new InvalidDataException("M4A was not created.");
            double duration = await DurationAsync(m4a);
            if (duration < 1.8 || duration > 2.3)
                throw new InvalidDataException(
                    "M4A duration differs from the 2-second audio track: " + duration);

            byte[] firstHash = SHA256.HashData(await File.ReadAllBytesAsync(m4a));
            string another = await AudioConversionService.ExtractAsync(
                source, folder, AudioOutputFormat.M4a, CancellationToken.None);
            if (another == m4a || !File.Exists(another))
                throw new IOException("Existing output must be preserved and numbered.");
            if (!SHA256.HashData(await File.ReadAllBytesAsync(m4a)).SequenceEqual(firstHash))
                throw new IOException("First converted file was modified.");

            string mp3 = await AudioConversionService.ExtractAsync(
                source, folder, AudioOutputFormat.Mp3, CancellationToken.None);
            if (Path.GetExtension(mp3) != ".mp3" || new FileInfo(mp3).Length < 1000)
                throw new InvalidDataException("MP3 was not generated.");
            if (!SHA256.HashData(await File.ReadAllBytesAsync(source)).SequenceEqual(sourceHash))
                throw new IOException("Source MP4 was modified.");

            if (Directory.EnumerateFiles(folder, "*velomux-stage-*").Any())
                throw new IOException("A staged temporary file was left after conversion.");

            Console.WriteLine("PASS: long Unicode name, short audio/long video, M4A, MP3,");
            Console.WriteLine("      output collision preserves first result, no staged files, originals intact.");
        }
        finally
        {
            try { Directory.Delete(root, recursive: true); } catch (IOException) { }
        }
    }

    private static async Task<double> DurationAsync(string path)
    {
        var result = await RunToolAsync("ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path);
        if (!double.TryParse(result.Trim(), NumberStyles.Float,
                            CultureInfo.InvariantCulture, out double seconds))
            throw new InvalidDataException("Output duration could not be read: " + result);
        return seconds;
    }

    private static async Task<string> RunToolAsync(string executable, params string[] args)
    {
        var p = new ProcessStartInfo(executable)
        {
            RedirectStandardError = true,
            RedirectStandardOutput = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        foreach (var a in args) p.ArgumentList.Add(a);
        using var process = Process.Start(p)
            ?? throw new IOException(executable + " could not start.");
        var stdout = process.StandardOutput.ReadToEndAsync();
        var stderr = process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        if (process.ExitCode != 0)
            throw new IOException(executable + " failed: " + await stderr);
        return await stdout;
    }
}
