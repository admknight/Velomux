using Avalonia;
using Avalonia.Controls;
using Avalonia.Media.Imaging;
using Avalonia.Interactivity;
using Avalonia.Input;
using Avalonia.Platform.Storage;
using Velomux.Desktop.Services;
using Velomux.Desktop.ViewModels;

namespace Velomux.Desktop;

public partial class MainWindow : Window
{
    private CancellationTokenSource? _activeBatch;
    private MainViewModel Vm => (MainViewModel)DataContext!;

    // The published EXE must pass this against its REAL opened Avalonia window
    // before GitHub publishes another evaluation artifact. Static XML checks
    // do not establish that runtime styles and state bindings are functional.
    internal void AssertInitialUiReady()
    {
        UpdateResponsiveShell();
        UpdateLayout();

        var empty = this.FindControl<StackPanel>("EmptyQueuePanel")
                    ?? throw new InvalidOperationException("Empty queue panel is missing.");
        var queued = this.FindControl<Grid>("QueueDataPanel")
                     ?? throw new InvalidOperationException("Queue data panel is missing.");
        var settings = this.FindControl<ScrollViewer>("SettingsViewport")
                       ?? throw new InvalidOperationException("Settings viewport is missing.");
        var m4a = this.FindControl<Button>("M4aFormatButton")
                  ?? throw new InvalidOperationException("M4A choice is missing.");
        var mp3 = this.FindControl<Button>("Mp3FormatButton")
                  ?? throw new InvalidOperationException("MP3 choice is missing.");
        if (!Vm.IsQueueEmpty || !empty.IsVisible || queued.IsVisible)
            throw new InvalidOperationException("Empty queue view is not correctly displayed.");
        if (!Vm.IsM4a || Vm.IsMp3 || !m4a.Classes.Contains("active")
            || mp3.Classes.Contains("active"))
            throw new InvalidOperationException("M4A/MP3 selected-format visual state is incorrect.");
        if (settings.Bounds.Width <= 0 || settings.Bounds.Height <= 0)
            throw new InvalidOperationException("Settings panel has no rendered layout dimensions.");

        // The previous layout passed compilation but its queue header forced
        // the entire right-hand settings panel off-screen at 1040px.
        // Check real, translated render bounds, not only XAML validity.
        foreach (var name in new[] { "QueuePanel", "SettingsPanel", "CreatorCredits" })
        {
            var panel = this.FindControl<Control>(name)
                        ?? throw new InvalidOperationException($"Missing layout element {name}.");
            if (!panel.IsVisible) continue; // Creator credits live in the compact header when narrow.
            var bottomRight = panel.TranslatePoint(
                new Point(panel.Bounds.Width, panel.Bounds.Height), this);
            if (bottomRight is null)
                throw new InvalidOperationException($"Cannot locate {name} on the window.");
            if (bottomRight.Value.X > Bounds.Width + 1 ||
                bottomRight.Value.Y > Bounds.Height + 1)
                throw new InvalidOperationException(
                    $"Layout overflow: {name} ends at {bottomRight.Value} " +
                    $"outside the visible {Bounds.Width}x{Bounds.Height} window.");
        }
        var nav = this.FindControl<Border>("NavSidebar")
                  ?? throw new InvalidOperationException("Navigation sidebar is missing.");
        var smallCredit = this.FindControl<TextBlock>("CompactCreator")
                          ?? throw new InvalidOperationException("Compact creator credit is missing.");
        if (Bounds.Width < 1250 && (nav.IsVisible || !smallCredit.IsVisible))
            throw new InvalidOperationException(
                "Compact mode did not reclaim the sidebar width or preserve author credit.");
        if (Bounds.Width >= 1250 && (!nav.IsVisible || smallCredit.IsVisible))
            throw new InvalidOperationException("Full-width sidebar mode is incorrect.");

        // Cancelling a file dialog must not change the initial ready status.
        string originalStatus = Vm.Status;
        Vm.AddFiles(Array.Empty<string>());
        if (Vm.Status != originalStatus)
            throw new InvalidOperationException("Empty file picker incorrectly changed status.");
    }

    public MainWindow()
    {
        InitializeComponent();
        DataContext = new MainViewModel();
        SizeChanged += (_, _) => UpdateResponsiveShell();
    }

    private void UpdateResponsiveShell()
    {
        // Keep two fully usable columns instead of shrinking buttons/fonts
        // until unreadable. The single pilot workflow needs no permanent
        // sidebar on screens below 1250 logical pixels.
        bool compact = Bounds.Width < 1250;
        var shell = this.FindControl<Grid>("AppShell");
        var sidebar = this.FindControl<Border>("NavSidebar");
        var credit = this.FindControl<TextBlock>("CompactCreator");
        if (shell is null || sidebar is null || credit is null) return;
        sidebar.IsVisible = !compact;
        shell.ColumnDefinitions[0].Width = new GridLength(
            compact ? 0 : 220, GridUnitType.Pixel);
        credit.IsVisible = compact;
    }

    internal void SaveStartupUiSnapshot()
    {
        var dir = Path.Combine(AppContext.BaseDirectory, "ui-qa");
        Directory.CreateDirectory(dir);
        int width = Math.Max(1, (int)Math.Ceiling(Bounds.Width));
        int height = Math.Max(1, (int)Math.Ceiling(Bounds.Height));
        string filename = Path.Combine(dir, "Avalonia-Windows-Startup.png");
        using var snapshot = new RenderTargetBitmap(new PixelSize(width, height));
        snapshot.Render(this);
        snapshot.Save(filename, PngBitmapEncoderOptions.Default);
        if (!File.Exists(filename) || new FileInfo(filename).Length < 5000)
            throw new IOException("The opened Avalonia window was not captured into a valid PNG.");
        Services.StartupDiagnostics.Record(
            $"GUI_SCREENSHOT: {filename} ({width}x{height}).");
    }

    private async void AddFiles_Click(object? sender, RoutedEventArgs e)
    {
        if (Vm.IsRunning) return;
        try
        {
            var files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
            {
                Title = "Select media containing audio",
                AllowMultiple = true,
            });
            Vm.AddFiles(files.Select(x => x.TryGetLocalPath())
                             .Where(x => !string.IsNullOrWhiteSpace(x))
                             .Select(x => x!));
        }
        catch (Exception ex)
        {
            Vm.Status = "File selection failed: " + ex.Message;
        }
    }

    private void Media_DragOver(object? sender, DragEventArgs e)
    {
        e.DragEffects = !Vm.IsRunning && e.DataTransfer.Contains(DataFormat.File)
            ? DragDropEffects.Copy
            : DragDropEffects.None;
        e.Handled = true;
    }

    private void Media_Drop(object? sender, DragEventArgs e)
    {
        if (Vm.IsRunning) return;
        var paths = e.DataTransfer.TryGetFiles()?.OfType<IStorageFile>()
            .Select(file => file.TryGetLocalPath())
            .Where(path => !string.IsNullOrWhiteSpace(path))
            .Select(path => path!);
        if (paths is not null) Vm.AddFiles(paths);
        e.Handled = true;
    }

    private void RemoveSelected_Click(object? sender, RoutedEventArgs e) => Vm.RemoveSelected();

    private void M4a_Click(object? sender, RoutedEventArgs e) =>
        Vm.Format = AudioOutputFormat.M4a;

    private void Mp3_Click(object? sender, RoutedEventArgs e) =>
        Vm.Format = AudioOutputFormat.Mp3;

    private async void ChooseFolder_Click(object? sender, RoutedEventArgs e)
    {
        if (Vm.IsRunning) return;
        try
        {
            var folders = await StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions
            {
                Title = "Choose output directory",
                AllowMultiple = false,
            });
            var selected = folders.FirstOrDefault()?.TryGetLocalPath();
            if (!string.IsNullOrWhiteSpace(selected)) Vm.OutputDirectory = selected;
        }
        catch (Exception ex)
        {
            Vm.Status = "Destination selection failed: " + ex.Message;
        }
    }

    private async void Convert_Click(object? sender, RoutedEventArgs e)
    {
        if (Vm.IsRunning || !Vm.Jobs.Any(j => j.Status != "Completed")) return;
        var folder = Vm.OutputDirectory.Trim();
        if (folder.Length == 0)
        {
            Vm.Status = "Please select a destination folder.";
            return;
        }

        _activeBatch = new CancellationTokenSource();
        Vm.IsRunning = true;
        var format = Vm.Format;
        try
        {
            foreach (var job in Vm.Jobs.ToList())
            {
                _activeBatch.Token.ThrowIfCancellationRequested();
                if (job.Status == "Completed") continue;

                job.Status = "Processing";
                job.Detail = "FFmpeg audio extraction in progress";
                Vm.Status = "Processing: " + job.FileName;
                try
                {
                    string saved = await AudioConversionService.ExtractAsync(
                        job.Path, folder, format, _activeBatch.Token);
                    job.Status = "Completed";
                    job.Detail = saved;
                    Vm.Status = "Saved: " + saved;
                }
                catch (OperationCanceledException)
                {
                    job.Status = "Cancelled";
                    job.Detail = "User cancelled. No partial file was published.";
                    Vm.Status = "Cancelled. Originals are unchanged.";
                    break;
                }
                catch (Exception ex)
                {
                    job.Status = "Failed";
                    job.Detail = ex.GetType().Name + ": " + ex.Message;
                    Vm.Status = "Failed: " + job.FileName + " — " + ex.Message;
                }
                finally
                {
                    Vm.NotifyFinished();
                }
            }
        }
        catch (OperationCanceledException)
        {
            Vm.Status = "Batch cancelled. Originals are unchanged.";
        }
        finally
        {
            Vm.IsRunning = false;
            _activeBatch.Dispose();
            _activeBatch = null;
            Vm.NotifyFinished();
        }
    }

    private void Cancel_Click(object? sender, RoutedEventArgs e) => _activeBatch?.Cancel();

    protected override void OnClosed(EventArgs e)
    {
        _activeBatch?.Cancel();
        base.OnClosed(e);
    }
}
