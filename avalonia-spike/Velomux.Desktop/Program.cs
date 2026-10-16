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
            BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
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

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .LogToTrace();
}
