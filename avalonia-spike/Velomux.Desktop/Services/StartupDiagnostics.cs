using System.Runtime.InteropServices;
using System.Text;

namespace Velomux.Desktop.Services;

/// <summary>
/// Windows GUI applications have no console: startup errors must never disappear.
/// The on-device log is local, excludes source media and contains only startup
/// events/exceptions. No telemetry or network requests are performed.
/// </summary>
public static class StartupDiagnostics
{
    public static string LogPath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Velomux", "Logs", "avalonia-startup.log");

    public static void Record(string message)
    {
        try
        {
            string path = LogPath;
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            // Append across launches: a failed run must not erase the evidence.
            File.AppendAllText(path,
                $"[{DateTimeOffset.Now:O}] [PID {Environment.ProcessId}] {message}{Environment.NewLine}",
                Encoding.UTF8);
        }
        catch (Exception)
        {
            // The logging mechanism must never itself stop the GUI from starting.
        }
    }

    public static void InstallHandlers()
    {
        AppDomain.CurrentDomain.UnhandledException += (_, e) =>
            Record("UNHANDLED: " + e.ExceptionObject);
        TaskScheduler.UnobservedTaskException += (_, e) =>
            Record("UNOBSERVED TASK: " + e.Exception);
    }

    public static void Fatal(Exception error, bool allowDialog)
    {
        Record("STARTUP FAILED:\n" + error);
        if (!allowDialog || !OperatingSystem.IsWindows())
            return;

        try
        {
            MessageBoxW(IntPtr.Zero,
                "Velomux could not open its window.\n\n"
                + error.GetType().Name + ": " + error.Message
                + "\n\nA diagnostic log was saved at:\n" + LogPath
                + "\n\nPlease share the log when reporting this problem.",
                "Velomux — startup error", 0x00000010 /* MB_ICONERROR */);
        }
        catch (Exception)
        {
            // Record remains on disk if the native error dialog is unavailable.
        }
    }

    [DllImport("user32.dll", EntryPoint = "MessageBoxW", CharSet = CharSet.Unicode)]
    private static extern int MessageBoxW(
        IntPtr owner, string message, string title, uint options);
}
