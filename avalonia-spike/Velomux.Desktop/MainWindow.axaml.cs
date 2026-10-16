using System.Globalization;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media.Imaging;
using Avalonia.Platform.Storage;
using Velomux.Desktop.Services;
using Velomux.Desktop.ViewModels;

namespace Velomux.Desktop;

public partial class MainWindow : Window
{
    private CancellationTokenSource? _activeBatch;
    private Task? _catalogLoadTask;
    private MainViewModel Vm => (MainViewModel)DataContext!;

    public MainWindow()
    {
        InitializeComponent();
        DataContext = new MainViewModel();
        SizeChanged += (_, _) => UpdateResponsiveShell();
        // Prevent wheel-hover on closed format/profile dropdowns from changing
        // the selected encoding operation. Scroll the settings viewport instead.
        AddHandler(InputElement.PointerWheelChangedEvent, ProtectWheelSelection, RoutingStrategies.Tunnel);
        Opened += (_, _) =>
        {
            UpdateResponsiveShell();
            _catalogLoadTask ??= LoadCatalogSafeAsync();
        };
    }

    private async Task LoadCatalogSafeAsync()
    {
        try
        {
            CatalogOption catalog = await MediaEngineBridge.LoadCatalogAsync();
            Vm.SetCatalog(catalog);
            var launchFiles = Environment.GetCommandLineArgs().Skip(1)
                .Where(arg => !arg.StartsWith("--", StringComparison.Ordinal)).ToList();
            if (launchFiles.Count > 0) Vm.AddFiles(launchFiles);
            Vm.AddActivity("Native Avalonia workstation ready.");
        }
        catch (Exception ex)
        {
            StartupDiagnostics.Record("ENGINE_CATALOG_FAILURE: " + ex);
            Vm.AddActivity("MEDIA ENGINE UNAVAILABLE: " + ex.Message);
        }
    }

    internal async Task EnsureCatalogLoadedAsync()
    {
        _catalogLoadTask ??= LoadCatalogSafeAsync();
        await _catalogLoadTask;
        if (!Vm.IsCatalogLoaded)
            throw new InvalidOperationException("Frozen Velomux backend did not provide its 51-preset catalog: " + Vm.Status);
    }

    private void UpdateResponsiveShell()
    {
        bool compact = Bounds.Width < 1260;
        var shell = this.FindControl<Grid>("AppShell");
        var sidebar = this.FindControl<Border>("NavSidebar");
        var credit = this.FindControl<TextBlock>("CompactCreator");
        var navigation = this.FindControl<WrapPanel>("CompactTaskBar");
        if (shell == null || sidebar == null || credit == null || navigation == null) return;
        sidebar.IsVisible = !compact;
        shell.ColumnDefinitions[0].Width = new GridLength(compact ? 0 : 218);
        credit.IsVisible = compact;
        navigation.IsVisible = compact;
        var columns = this.FindControl<Grid>("WorkspaceColumns");
        if (columns != null)
            columns.ColumnDefinitions[1].Width = new GridLength(compact ? 340 : 410);
        var activity = this.FindControl<StackPanel>("ActivityPanel");
        if (activity != null) activity.IsVisible = Bounds.Height >= 790;
    }

    internal void AssertInitialUiReady()
    {
        UpdateResponsiveShell();
        UpdateLayout();
        if (!Vm.IsCatalogLoaded || Vm.Tasks.Count != 7 ||
            Vm.Profiles.Count < 2 || Vm.VisiblePresets.Count != 51)
            throw new InvalidOperationException("Task and preset controls are not populated.");
        if (!Vm.IsQueueEmpty)
            throw new InvalidOperationException("Initial queue must be empty for GUI startup QA.");
        var empty = this.FindControl<StackPanel>("EmptyQueuePanel")
                    ?? throw new InvalidOperationException("Missing empty-queue state.");
        var queue = this.FindControl<Grid>("QueueDataPanel")
                    ?? throw new InvalidOperationException("Missing file queue.");
        var settings = this.FindControl<ScrollViewer>("SettingsViewport")
                    ?? throw new InvalidOperationException("Missing settings viewport.");
        if (!empty.IsVisible || queue.IsVisible || settings.Bounds.Height <= 0)
            throw new InvalidOperationException("Initial Avalonia layout is inconsistent.");
        foreach (var key in new[] { "QueuePanel", "SettingsPanel" })
        {
            var panel = this.FindControl<Control>(key)
                ?? throw new InvalidOperationException("Missing panel: " + key);
            var bottomRight = panel.TranslatePoint(
                new Point(panel.Bounds.Width, panel.Bounds.Height), this);
            if (bottomRight == null || bottomRight.Value.X > Bounds.Width + 1
                || bottomRight.Value.Y > Bounds.Height + 1)
                throw new InvalidOperationException(
                    $"Off-screen panel detected: {key}, bottom-right={bottomRight}, panel={panel.Bounds}, window={Bounds}.");
        }
        var sidebar = this.FindControl<Border>("NavSidebar")!;
        var bar = this.FindControl<WrapPanel>("CompactTaskBar")!;
        if (Bounds.Width < 1260 ? (sidebar.IsVisible || !bar.IsVisible)
                                : (!sidebar.IsVisible || bar.IsVisible))
            throw new InvalidOperationException("Responsive navigation layout mismatch.");
    }

    internal void SaveStartupUiSnapshot()
    {
        var dir = Path.Combine(AppContext.BaseDirectory, "ui-qa");
        Directory.CreateDirectory(dir);
        var size = new PixelSize(
            Math.Max(1, (int)Math.Ceiling(Bounds.Width)),
            Math.Max(1, (int)Math.Ceiling(Bounds.Height)));
        string path = Path.Combine(dir, "Avalonia-Windows-Startup.png");
        using var bitmap = new RenderTargetBitmap(size);
        bitmap.Render(this);
        bitmap.Save(path, PngBitmapEncoderOptions.Default);
        if (!File.Exists(path) || new FileInfo(path).Length < 5000)
            throw new IOException("The full-workstation screenshot was not captured.");
        StartupDiagnostics.Record($"GUI_SCREENSHOT: {path} ({size.Width}x{size.Height}).");
    }

    private void ProtectWheelSelection(object? sender, PointerWheelEventArgs e)
    {
        for (Control? current = e.Source as Control; current != null;
             current = current.Parent as Control)
        {
            if (current is not ComboBox combo) continue;
            if (combo.IsDropDownOpen) return;
            e.Handled = true;
            if (this.FindControl<ScrollViewer>("SettingsViewport") is { } viewer)
            {
                double max = Math.Max(0, viewer.Extent.Height - viewer.Viewport.Height);
                viewer.Offset = new Vector(viewer.Offset.X,
                    Math.Clamp(viewer.Offset.Y - e.Delta.Y * 45, 0, max));
            }
            return;
        }
    }

    private void ChooseTask_Click(object? sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is string id) Vm.ChooseTask(id);
    }
    private void QuickMode_Click(object? sender, RoutedEventArgs e) => Vm.QuickMode = true;
    private void AdvancedMode_Click(object? sender, RoutedEventArgs e) => Vm.QuickMode = false;

    private async void AddFiles_Click(object? sender, RoutedEventArgs e)
    {
        if (Vm.IsRunning) return;
        try
        {
            var files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
            {
                Title = "Select video, audio or image files",
                AllowMultiple = true
            });
            Vm.AddFiles(files.Select(x => x.TryGetLocalPath())
                .Where(x => !string.IsNullOrWhiteSpace(x)).Select(x => x!));
        }
        catch (Exception ex) { Vm.AddActivity("File selection failed: " + ex.Message); }
    }
    private async void AddFolder_Click(object? sender, RoutedEventArgs e)
    {
        if (Vm.IsRunning) return;
        try
        {
            var folders = await StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions
            {
                Title = "Import media directory",
                AllowMultiple = false
            });
            var root = folders.FirstOrDefault()?.TryGetLocalPath();
            if (!string.IsNullOrWhiteSpace(root))
            {
                var files = Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories);
                Vm.AddFiles(files, Path.GetFullPath(root));
            }
        }
        catch (Exception ex) { Vm.AddActivity("Folder import failed: " + ex.Message); }
    }

    private void Media_DragOver(object? sender, DragEventArgs e)
    {
        e.DragEffects = !Vm.IsRunning && e.DataTransfer.Contains(DataFormat.File)
            ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }
    private void Media_Drop(object? sender, DragEventArgs e)
    {
        if (Vm.IsRunning) return;
        var files = e.DataTransfer.TryGetFiles();
        if (files != null)
        {
            foreach (var item in files)
            {
                if (item is IStorageFolder folder)
                {
                    var root = folder.TryGetLocalPath();
                    if (!string.IsNullOrWhiteSpace(root))
                    {
                        try { Vm.AddFiles(Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories), root); }
                        catch (Exception ex) { Vm.AddActivity("Folder drop error: " + ex.Message); }
                    }
                }
                else if (item is IStorageFile file)
                {
                    var path = file.TryGetLocalPath();
                    if (!string.IsNullOrWhiteSpace(path)) Vm.AddFiles(new[] { path });
                }
            }
        }
        e.Handled = true;
    }
    private void RemoveSelected_Click(object? sender, RoutedEventArgs e) => Vm.RemoveSelected();
    private void ClearCompleted_Click(object? sender, RoutedEventArgs e) => Vm.ClearCompleted();

    private async void Inspect_Click(object? sender, RoutedEventArgs e)
    {
        if (Vm.SelectedJob is not MediaJob selected) return;
        try { Vm.MediaInfo = await MediaEngineBridge.DescribeAsync(selected.Path); }
        catch (Exception ex) { Vm.MediaInfo = "Unable to inspect: " + ex.Message; }
    }
    private async void ChooseFolder_Click(object? sender, RoutedEventArgs e)
    {
        if (Vm.IsRunning) return;
        try
        {
            var folders = await StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions
            {
                Title = "Choose where outputs are saved",
                AllowMultiple = false
            });
            var path = folders.FirstOrDefault()?.TryGetLocalPath();
            if (!string.IsNullOrWhiteSpace(path)) Vm.OutputDirectory = path;
        }
        catch (Exception ex) { Vm.AddActivity("Destination picker failed: " + ex.Message); }
    }

    private static double ParseNumber(string value, string label, double minimum, double maximum)
    {
        if (!double.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out double result)
            || !double.IsFinite(result) || result < minimum || result > maximum)
            throw new ArgumentException($"{label} must be a number between {minimum} and {maximum}.");
        return result;
    }

    private static string DestinationFor(MediaJob job, string baseDirectory, bool preserve)
    {
        if (!preserve || job.ImportRoot == null) return baseDirectory;
        string relative = Path.GetRelativePath(job.ImportRoot, job.Path);
        if (Path.IsPathRooted(relative) || relative == ".." ||
            relative.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal))
            return baseDirectory;
        string? folder = Path.GetDirectoryName(relative);
        return string.IsNullOrEmpty(folder) ? baseDirectory : Path.Combine(baseDirectory, folder);
    }

    private async void Convert_Click(object? sender, RoutedEventArgs e)
    {
        if (!Vm.CanStart) return;
        string preset = Vm.SelectedPresetName;
        if (string.IsNullOrWhiteSpace(preset))
        {
            Vm.AddActivity("Select a conversion profile or advanced encoder preset.");
            return;
        }
        if (string.IsNullOrWhiteSpace(Vm.OutputDirectory))
        {
            Vm.AddActivity("Select an output destination.");
            return;
        }
        string directory;
        Dictionary<string, object> options;
        try
        {
            directory = Path.GetFullPath(Vm.OutputDirectory.Trim());
            double start = ParseNumber(Vm.TrimStart, "Trim start", 0, 1000000);
            double end = ParseNumber(Vm.TrimEnd, "Trim end", 0, 1000000);
            double speed = ParseNumber(Vm.Speed, "Playback speed", 0.5, 2);
            int quality = (int)ParseNumber(Vm.Quality, "Video CRF", 0, 51);
            int imageQuality = (int)ParseNumber(Vm.ImageQuality, "Image quality", 0, 100);
            if (end != 0 && end <= start)
                throw new ArgumentException("Trim end must be greater than trim start.");
            if (Vm.QuickMode && Vm.SelectedTask?.Id == "trim" && end == 0 && start == 0)
                throw new ArgumentException("Choose a trim start or end time before running Trim.");
            if (Vm.Collision == "repair" && (start != 0 || end != 0 || speed != 1))
                throw new ArgumentException("Repair cannot verify previous output settings after a trim or speed change; choose Rename.");
            options = new()
            {
                ["collision"] = Vm.Collision,
                ["trim_start"] = start,
                ["trim_end"] = end,
                ["media_speed"] = speed,
                ["quality"] = quality,
                ["image_quality"] = imageQuality,
                ["audio_normalize"] = Vm.Normalize,
                ["decode_check"] = Vm.FullDecode,
            };
        }
        catch (Exception ex) { Vm.AddActivity("Invalid conversion settings: " + ex.Message); return; }

        bool preserve = Vm.PreserveFolders;
        bool quick = Vm.QuickMode;
        var task = Vm.SelectedTask;
        var advanced = Vm.SelectedPreset;
        _activeBatch = new CancellationTokenSource();
        var cancellation = _activeBatch;
        Vm.IsRunning = true;
        Vm.AddActivity("Started batch · " + preset);
        try
        {
            foreach (var job in Vm.Jobs.ToList())
            {
                if (cancellation.IsCancellationRequested) break;
                if (job.Status == "Completed") continue;
                bool compatible = quick
                    ? task?.InputKinds.Contains(Vm.Classify(job.Path)) == true
                    : advanced?.Group == "audio"
                        ? Vm.Classify(job.Path) is "audio" or "video"
                        : advanced?.Group == Vm.Classify(job.Path);
                if (!compatible)
                {
                    job.Status = "Failed";
                    job.Detail = "Selected task and input type are incompatible.";
                    Vm.AddActivity("Incompatible input: " + job.FileName);
                    Vm.RefreshQueue();
                    continue;
                }
                job.Status = "Processing";
                job.Progress = 0;
                job.Detail = "Starting validated conversion...";
                Vm.RefreshQueue();
                try
                {
                    var progress = new Progress<EngineProgress>(value =>
                    {
                        job.Progress = value.Percent;
                        job.Detail = value.Detail;
                    });
                    var result = await MediaEngineBridge.ConvertAsync(
                        job.Path, DestinationFor(job, directory, preserve),
                        preset, options, progress, cancellation.Token);
                    job.Status = result.Status switch
                    {
                        "done" => "Completed",
                        "skipped" => "Skipped",
                        "cancelled" => "Cancelled",
                        _ => "Failed"
                    };
                    job.Progress = job.Status == "Completed" ? 100 : job.Progress;
                    job.Detail = result.Output.Length > 0 ? result.Output : result.Detail;
                    Vm.AddActivity($"{job.Status}: {job.FileName}" +
                        (result.Status == "failed" ? " — " + result.Detail : ""));
                }
                catch (Exception ex)
                {
                    job.Status = cancellation.IsCancellationRequested ? "Cancelled" : "Failed";
                    job.Detail = ex.Message;
                    Vm.AddActivity($"{job.Status}: {job.FileName} — {ex.Message}");
                }
                finally { Vm.RefreshQueue(); }
            }
            if (cancellation.IsCancellationRequested)
                Vm.AddActivity("Batch cancelled. Existing outputs and source files were not overwritten by a cancelled job.");
        }
        finally
        {
            Vm.IsRunning = false;
            cancellation.Dispose();
            _activeBatch = null;
            Vm.RefreshQueue();
        }
    }

    private void Cancel_Click(object? sender, RoutedEventArgs e) => _activeBatch?.Cancel();
    protected override void OnClosed(EventArgs e)
    {
        _activeBatch?.Cancel();
        base.OnClosed(e);
    }
}
