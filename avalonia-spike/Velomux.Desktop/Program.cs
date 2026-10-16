using Avalonia;

namespace Velomux.Desktop;

internal static class Program
{
    [STAThread]
    public static int Main(string[] args)
    {
        if (args.Contains("--media-integration-test"))
        {
            try
            {
                Services.MediaIntegrationTest.RunAsync().GetAwaiter().GetResult();
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine(ex);
                return 42;
            }
        }

        bool desktopSmoke = args.Contains("--desktop-startup-test");
        Services.StartupDiagnostics.InstallHandlers();
        Services.StartupDiagnostics.Record(
            "BEGIN: Avalonia desktop launch; OS=" + Environment.OSVersion
            + "; runtime=" + Environment.Version
            + "; executable=" + Environment.ProcessPath
            + "; smoke=" + desktopSmoke);
        try
        {
            BuildAvaloniaApp(forceSoftwareRendering: args.Contains("--software-rendering"))
                .StartWithClassicDesktopLifetime(args);
            Services.StartupDiagnostics.Record(
                "END: Avalonia desktop session; exit=" + Environment.ExitCode);
            return Environment.ExitCode;
        }
        catch (Exception ex)
        {
            Services.StartupDiagnostics.Fatal(ex, allowDialog: !desktopSmoke);
            return 43;
        }
    }

    public static AppBuilder BuildAvaloniaApp(bool forceSoftwareRendering = false)
    {
        var builder = AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .LogToTrace();

        // Keep the default ANGLE->software fallback, with an explicit
        // troubleshooting path for Windows graphics-driver problems.
        if (forceSoftwareRendering && OperatingSystem.IsWindows())
        {
            Services.StartupDiagnostics.Record("GPU diagnostic mode: software renderer requested.");
            builder = builder.With(new Win32PlatformOptions
            {
                RenderingMode = new[] { Win32RenderingMode.Software }
            });
        }
        return builder;
    }
}
