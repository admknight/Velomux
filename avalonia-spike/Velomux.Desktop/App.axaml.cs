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
            var window = new MainWindow();
            desktop.MainWindow = window;
            StartupDiagnostics.Record("MainWindow constructor completed.");
            window.Opened += async (_, _) =>
            {
                StartupDiagnostics.Record(
                    "MainWindow.Opened; IsVisible=" + window.IsVisible
                    + "; size=" + window.Bounds.Size);
                if (!Environment.GetCommandLineArgs().Contains("--desktop-startup-test"))
                    return;
                bool healthy = window.IsVisible;
                try
                {
                    // A visible window without the 51-preset engine is NOT a passing app.
                    await window.EnsureCatalogLoadedAsync();
                    await Dispatcher.UIThread.InvokeAsync(() =>
                    {
                        window.AssertInitialUiReady();
                        window.SaveStartupUiSnapshot();
                    }, DispatcherPriority.Background);
                    StartupDiagnostics.Record(
                        "GUI_INITIAL_STATE: PASS (seven workflows, 29 quick profiles, 51 presets, responsive layout)");
                }
                catch (Exception ex)
                {
                    healthy = false;
                    StartupDiagnostics.Record("GUI_INITIAL_STATE: FAIL " + ex);
                }
                StartupDiagnostics.Record(
                    "DESKTOP_STARTUP_TEST: " + (healthy ? "PASS" : "FAIL"));
                desktop.Shutdown(healthy ? 0 : 51);
            };
        }
        base.OnFrameworkInitializationCompleted();
    }
}
