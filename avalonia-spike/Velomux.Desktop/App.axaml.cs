using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Avalonia.Threading;
using Velomux.Desktop.Services;

namespace Velomux.Desktop;

public partial class App : Application
{
    public override void Initialize()
    {
        StartupDiagnostics.Record("App.Initialize: loading compiled XAML.");
        AvaloniaXamlLoader.Load(this);
        StartupDiagnostics.Record("App.Initialize: compiled XAML loaded.");
    }

    public override void OnFrameworkInitializationCompleted()
    {
        StartupDiagnostics.Record("OnFrameworkInitializationCompleted: creating main window.");
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.MainWindow = new MainWindow();
            StartupDiagnostics.Record("MainWindow constructor completed.");
            desktop.MainWindow.Opened += (_, _) =>
            {
                StartupDiagnostics.Record(
                    "MainWindow.Opened; IsVisible=" + desktop.MainWindow.IsVisible
                    + "; size=" + desktop.MainWindow.Bounds.Size);
                if (Environment.GetCommandLineArgs().Contains("--desktop-startup-test"))
                {
                    Dispatcher.UIThread.Post(() =>
                    {
                        bool healthy = desktop.MainWindow?.IsVisible == true;
                        if (healthy && desktop.MainWindow is MainWindow window)
                        {
                            try
                            {
                                window.AssertInitialUiReady();
                                StartupDiagnostics.Record(
                                    "GUI_INITIAL_STATE: PASS (empty queue, selected M4A, settings layout)");
                            }
                            catch (Exception ex)
                            {
                                healthy = false;
                                StartupDiagnostics.Record("GUI_INITIAL_STATE: FAIL " + ex);
                            }
                        }
                        StartupDiagnostics.Record(
                            "DESKTOP_STARTUP_TEST: " + (healthy ? "PASS" : "FAIL"));
                        desktop.Shutdown(healthy ? 0 : 51);
                    }, DispatcherPriority.Background);
                }
            };
        }
        base.OnFrameworkInitializationCompleted();
    }
}
