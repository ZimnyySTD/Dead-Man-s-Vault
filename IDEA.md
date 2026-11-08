# DEAD MAN'S VAULT
## Project Idea & Software Specification

**Platform:** Windows  
**Project Type:** Desktop Game Launcher  
**Core Technology:** Existing B2Chunks implementation  
**Status:** Project Concept

---

# 1. Overview

Dead Man's Vault is a lightweight, high-performance Windows game launcher designed to make importing, downloading, installing, organizing, and launching portable games as fast and straightforward as possible.

The launcher supports three primary methods of adding games:

1. Importing existing game folders.
2. Downloading and installing conventional compressed game archives.
3. Downloading and installing games distributed through the existing B2Chunks system.

Dead Man's Vault also supports a shareable `games.json` format that allows developers and users to create, distribute, and import game libraries.

The launcher focuses on performance, simplicity, reliability, and minimal resource consumption.

It is not intended to become a gaming platform or storefront. Its purpose is to provide an efficient way to manage and launch games.

# 2. Core Philosophy

Dead Man's Vault should follow several fundamental principles:

- Extremely fast application startup.
- Minimal CPU and RAM consumption.
- Fast downloads and extraction.
- Efficient game launching.
- Lightweight and responsive interface.
- Simple game importing.
- Portable game installations.
- No unnecessary background services.
- No accounts or mandatory online services.
- Native Windows integration wherever practical.

The launcher should remain lightweight even when managing a large game library.

# 3. Game Library

The game library is the primary interface of Dead Man's Vault.

It displays all registered games, their artwork, logos, names, versions, and installation status.

Each game should have a dedicated entry containing:

- Game name.
- Cover artwork.
- Game logo, when available.
- Description.
- Version.
- Installation status.
- Installation location.
- Executable path.
- Download source.
- Additional metadata.

The library should support:

- Grid and list layouts.
- Game searching.
- Sorting.
- Filtering.
- Game details pages.
- Installing games.
- Launching installed games.
- Removing games from the library.
- Managing game locations.

Installed and available games should be distinguishable.

# 4. Automatic Game Metadata Retrieval

One of the main features of Dead Man's Vault is automatic game metadata retrieval.

When a developer adds a game to `games.json`, they only need to provide its name.

The launcher can then search a supported public game database using that name.

If a matching game is found, the launcher retrieves available metadata, including:

- Game title.
- Cover artwork.
- Background artwork.
- Game logo.
- Description.
- Release date.
- Developer.
- Publisher.
- Genre.
- Other available information.

This information is displayed in the library.

### Metadata lookup workflow

1. A game is added to `games.json`.
2. The launcher reads its name.
3. The metadata service searches for matching games.
4. The launcher identifies the most likely match.
5. The user can confirm or select another result if necessary.
6. Available artwork and metadata are retrieved.
7. The metadata is cached locally.
8. The game appears in the library with its artwork.

Metadata retrieval should be optional and must never prevent a game from being imported or installed.

If no matching game is found, the launcher should use a fallback appearance.

The launcher should also allow manually changing artwork and metadata.

Metadata providers should be configurable, and their API requirements, attribution rules, and usage limits should be respected.

# 5. Game Importing

Dead Man's Vault supports three different game importing methods.

## 5.1 Local Folder Import

Users can select an existing game folder on their computer.

The launcher registers the folder as a locally available game.

Characteristics:

- No downloading.
- No extraction.
- No modification of shared `games.json`.
- Manual executable selection when necessary.
- Automatic metadata retrieval using the game name, when available.

Local folder imports are stored in the user's local library.

## 5.2 Direct Archive Download

Users can provide a direct download URL to a compressed game archive.

Supported formats should include:

- ZIP.
- RAR.
- 7z.
- Other formats supported by the selected extraction libraries.

Installation workflow:

1. Download the archive.
2. Display download progress.
3. Verify the downloaded file where checksums are available.
4. Extract the archive.
5. Ask the user to select the game's executable.
6. Save the executable path.
7. Register the installation.
8. Display the game in the library.

The installation should support cancellation and useful error reporting.

## 5.3 B2Chunks Import

Dead Man's Vault integrates with the existing B2Chunks project.

B2Chunks is an already-developed technology with its own repository, implementation, and documentation.

The launcher should use the existing implementation rather than recreating or redesigning the protocol.

The user provides:

- B2Chunks manifest.
- Chunk download sources or URLs as required by the existing format.
- Optional public signature information.

Installation workflow:

1. Retrieve the manifest.
2. Process the package using the existing B2Chunks implementation.
3. Download the required chunks.
4. Reconstruct and extract the original game package according to B2Chunks.
5. Ask the user to select the executable.
6. Save the installation information.
7. Register the game.

The launcher should provide a unified progress interface for B2Chunks downloads and installation.

# 6. games.json

`games.json` is the primary shareable game library definition format.

Users and developers can create their own game collections and distribute them to other Dead Man's Vault users.

A new launcher installation should include an empty default `games.json`.

Users can add games to it and export the resulting file.

### Example structure

    {
      "format": "DMV",
      "version": 1,
      "games": [
        {
          "id": "example-game",
          "name": "Example Game",
          "version": "1.0.0",
          "description": "An example game.",
          "source": {
            "type": "b2",
            "manifest": "https://example.com/manifest.json"
          },
          "executable": "Game.exe"
        }
      ]
    }

The example is illustrative; the final schema should be defined by the implementation.

### Important behavior

- Games can be added to the definition.
- Games can be removed.
- Definitions can be imported.
- Definitions can be exported.
- Definitions can be shared.
- Definitions can be validated.
- Games can be installed directly from their definitions.

The game name should be sufficient to initiate metadata lookup.

The executable path should be included when known so that users importing an already-configured game definition do not need to select the executable again.

Shared definitions must not contain machine-specific installation paths.

Local installation state should be stored separately.

# 7. Installation Manager

All game installation methods should use one central installation management system.

The installation manager coordinates the different download and extraction backends.

Responsibilities include:

- Download management.
- Extraction.
- Installation directory selection.
- Progress reporting.
- Cancellation.
- Error handling.
- Executable selection.
- Installation registration.

The interface should display:

- Current installation stage.
- Download speed.
- Download progress.
- Downloaded size.
- Extraction progress.
- Overall installation status.

The installer should avoid unnecessary memory usage and use efficient filesystem operations.

Archive extraction must also safely handle malicious paths and prevent files from escaping the selected installation directory.

# 8. Game Executable Management

After installing a game, Dead Man's Vault asks the user to select the game's executable.

This selection is saved in the local installation metadata and, when appropriate, in the shared game definition as a relative executable path.

This prevents users from having to select the executable repeatedly.

The launcher should support:

- Executable selection.
- Executable path validation.
- Custom launch arguments.
- Working directory configuration.
- Per-game launch settings.

If an executable is missing, the launcher should allow the user to locate it again.

# 9. Game Runner

The game runner is responsible for launching installed games.

It should be extremely lightweight and initialize only the functionality necessary to start a game.

Responsibilities:

- Validate executable paths.
- Start the game process.
- Apply launch arguments.
- Set the working directory.
- Track the game's running state.
- Detect when the game exits.
- Update the library accordingly.

Launching a game should not initialize the download manager or perform unnecessary library scans.

The launcher should not interfere with the game's normal execution.

# 10. Download Manager

The download manager handles ordinary archive downloads and integrates with the B2Chunks backend.

Features:

- Download progress.
- Download speed.
- Downloaded file size.
- Cancellation.
- Retry on failure.
- Configurable download concurrency.
- Efficient disk writing.
- Temporary file management.

Downloads should use asynchronous operations where appropriate.

The download manager should avoid blocking the UI thread.

# 11. Developer Mode

Dead Man's Vault includes a hidden developer mode.

It can be activated by triple-clicking the launcher's build number.

Developer mode provides access to additional diagnostic and debugging functionality.

### Developer features

**Performance monitoring**
- Application CPU usage.
- Application memory usage.
- System RAM information.
- System CPU information.
- GPU information where available.
- Frame rate monitoring for supported overlays.

**Debugging**
- Application logs.
- Download diagnostics.
- Installation diagnostics.
- Error information.
- Internal application state.
- Debug console.

**Debug overlay**

An optional overlay can display performance information while using the launcher.

The overlay is disabled by default.

Game-specific FPS monitoring requires appropriate graphics integration and should be treated separately from launcher performance monitoring.

# 12. User Interface

The visual identity of Dead Man's Vault should follow a dark, minimal, premium desktop aesthetic.

Suggested design characteristics:

- Dark charcoal background.
- Subtle metallic surfaces.
- Muted amber or orange accent colors.
- Clean typography.
- Minimal visual clutter.
- Smooth but restrained animations.
- Clear progress indicators.
- Game artwork as the main visual element.

### Main navigation

- Library.
- Downloads.
- Add Game.
- Settings.

Developer mode should be accessible through the build number Easter egg.

The interface should prioritize responsiveness and fast navigation over unnecessary visual effects.

# 13. Settings

The settings section should provide:

**General**
- Application appearance.
- Language, if supported.
- Startup behavior.
- Confirmation preferences.

**Storage**
- Default game installation directory.
- Download temporary directory.
- Cache location.
- Storage information.

**Downloads**
- Maximum concurrent downloads.
- Download retry behavior.
- Temporary file cleanup.

**Library**
- Default layout.
- Sorting preferences.
- Metadata retrieval settings.
- Artwork cache management.

**Developer**
- Debug mode.
- Logging options.
- Debug overlay configuration.

# 14. Local Data Management

Dead Man's Vault should distinguish between shared game definitions and local application data.

Suggested local data categories:

- Game library definitions.
- Installed game records.
- Executable paths.
- Installation directories.
- User settings.
- Metadata cache.
- Artwork cache.
- Download state.
- Application logs.

The launcher should avoid repeatedly scanning large game directories during startup.

Cached information should be used wherever possible.

# 15. Performance Requirements

Performance is one of the most important aspects of Dead Man's Vault.

The application should be designed to minimize unnecessary work.

### Startup performance

- Fast initialization.
- Minimal startup dependencies.
- Efficient metadata loading.
- No unnecessary filesystem scanning.
- Lazy initialization of nonessential systems.

### Memory performance

- Avoid loading unnecessary artwork at full resolution.
- Cache metadata efficiently.
- Avoid keeping large archives in memory.
- Stream files during downloads and extraction where supported.
- Release temporary resources promptly.

### UI performance

- Keep UI operations separate from heavy background tasks.
- Use asynchronous downloads and extraction.
- Avoid blocking rendering.
- Avoid excessive animations and effects.

### Game launching

Launching a game should be a direct and lightweight operation.

The launcher should not introduce unnecessary background resource consumption while the game is running.

Dead Man's Vault can optimize its own startup, installation, and launching overhead, but should not claim to improve the game's internal FPS or rendering performance.

# 16. Technical Direction

The launcher is a Windows-first desktop application.

Potential implementation technologies include:

- C++ or Rust for the core application.
- Native Windows APIs for filesystem and process operations.
- A lightweight desktop UI framework.
- Zstandard or other suitable archive libraries where appropriate.
- An asynchronous HTTP implementation.
- JSON for configuration and library definitions.
- The existing B2Chunks implementation for chunked game distribution.

The final technology stack should prioritize performance, maintainability, and compatibility with the B2Chunks repository.

# 17. Project Structure

Suggested organization:

    DeadMansVault/
    │
    ├── Launcher/
    │   ├── Core/
    │   ├── Application/
    │   ├── UI/
    │   └── Settings/
    │
    ├── Library/
    │   ├── GameRegistry/
    │   ├── GameMetadata/
    │   ├── GameArtwork/
    │   └── GameDefinitions/
    │
    ├── DownloadManager/
    │   ├── HTTP/
    │   ├── Queue/
    │   └── Progress/
    │
    ├── Installer/
    │   ├── ArchiveInstaller/
    │   ├── B2ChunksInstaller/
    │   ├── Extraction/
    │   └── Registration/
    │
    ├── GameRunner/
    │
    ├── DeveloperMode/
    │   ├── Diagnostics/
    │   ├── Monitoring/
    │   ├── Logging/
    │   └── Overlay/
    │
    ├── Storage/
    │   ├── Configuration/
    │   ├── Cache/
    │   └── LocalDatabase/
    │
    └── Resources/

The existing B2Chunks project should remain an external dependency or integrated component according to its actual repository architecture.

# 18. Development Roadmap

### Phase 1 — Foundation
- Establish Windows application foundation.
- Implement core application lifecycle.
- Establish settings and local storage.
- Build the initial interface.

### Phase 2 — Library
- Implement game registry.
- Implement games.json import and export.
- Implement local folder importing.
- Implement game searching and sorting.

### Phase 3 — Metadata
- Integrate a public game metadata database.
- Implement name-based game searching.
- Retrieve artwork and descriptions.
- Implement metadata caching.
- Allow manual metadata selection and editing.

### Phase 4 — Installation
- Implement ordinary archive downloads.
- Implement archive extraction.
- Implement installation directory management.
- Implement executable selection.
- Implement installation registration.

### Phase 5 — B2Chunks
- Inspect the existing B2Chunks repository.
- Integrate the existing implementation.
- Implement manifest importing.
- Implement chunk downloads.
- Implement reconstruction and installation.
- Connect progress reporting to the common installer.

### Phase 6 — Game Runner
- Implement executable launching.
- Implement launch arguments.
- Implement running-state detection.
- Implement per-game settings.

### Phase 7 — Developer Mode
- Implement triple-click activation.
- Implement diagnostics.
- Implement performance monitoring.
- Implement debug overlay.

### Phase 8 — Optimization
- Optimize startup.
- Optimize memory consumption.
- Optimize installation performance.
- Optimize library rendering.
- Test large game libraries.
- Test interrupted downloads and installation failures.

# 19. Features Explicitly Outside the Project Scope

Dead Man's Vault is not intended to implement:

- Automatic game updates.
- Delta updates.
- Game patching.
- Game storefronts.
- User accounts.
- Friends lists.
- Multiplayer functionality.
- Cloud saves.
- Social features.
- Mandatory online authentication.
- A replacement for B2Chunks.

These features are intentionally excluded to keep the project focused.

# 20. Final Vision

Dead Man's Vault should be a fast, clean, and reliable Windows game launcher.

Its main purpose is to simplify the process of obtaining and launching portable games.

Users should be able to import a game from a folder, download a conventional archive, or install a B2Chunks package without having to understand the underlying installation process.

Developers should be able to create and share `games.json` files containing game definitions, download sources, executable information, and metadata.

The launcher should automatically retrieve game artwork and information when possible, creating an attractive library without requiring developers to manually provide every image.

Above all, Dead Man's Vault should remain lightweight.

**The ideal experience is simple: open the launcher, choose a game, install it if necessary, and play.**

No unnecessary complexity. No bloated platform. Just a fast and efficient game launcher.
