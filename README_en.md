# Wuthering Waves Score Helper

English | [中文](README.md)

Wuthering Waves Score Helper is a game automation tool for Wuthering Waves, built on [ok-script](https://github.com/ok-oldking/ok-script).

### Demo

**API list and script recording**

![image_scripting](docs/images/image_scripting.png)

**Capture and interaction methods**

![image_screenshot](docs/images/image_capture.png)

**Annotation management and template matching**

![image_template](docs/images/image_template.png)
![image_markup](docs/images/image_markup.png)

## What Is Included

- A runnable ok-script GUI application entry point.
- `MyOneTimeTask`, a sample task that demonstrates common task APIs and config widgets.
- Config widget examples: drop-down, boolean, integer, float, string, text edit, list, multi-selection, file selector, folder selector, global config, and button groups.
- OCR, relative-region OCR, and template matching examples.
- A `ConfigOption` global configuration example.
- `TaskTestCase` automated test examples.
- i18n `.po` files and compiled `.mo` files.
- `pyappify.yml` and GitHub Actions packaging/release configuration.

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/konghui111/konghuiww.git
cd konghuiww
```

### 2. Install Python 3.12 and Create a Virtual Environment

Install [Python 3.12.10](https://www.python.org/downloads/release/python-31210/), the last full Python 3.12 maintenance release with Windows installers, then run these commands in the repository:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt --upgrade
```

Administrator privileges are normally unnecessary. If the target game runs as administrator, launch the automation app with the same privilege level or capture and input may not work.

### 3. Adapt `src/config.py` to the Game

At minimum, review and update:

- `gui_title`: the application window title.
- `windows`: executable names, window class, interaction methods, and capture methods for a native Windows game.
- `adb.packages`: package names for a game running on an emulator or Android device.
- `browser`: URL, display name, and browser resolution for a browser game.
- `supported_resolution`: supported aspect ratio and minimum resolution.
- `links`: project, support, and community links.

Configure at least one of `windows`, `adb`, or `browser`. A project may support multiple target types at the same time. A browser configuration example is included in `src/config.py`. Browser targets also require `playwright`; add it to `requirements.in` and the locked `requirements.txt` so local runs and GitHub builds include it. If window or device information is unknown, start in Debug mode and identify it there.

### 4. Replace the Application Icons

Replace `icons/icon.png` and `icons/icon.ico` with your own icons. Keeping these filenames avoids configuration changes. If you rename them, also update `src/config.py` and `pyappify.yml`.

### 5. Configure the Update Repository

Update each profile's `name` and `git_url` in `pyappify.yml`:

- For production releases, point `git_url` to a separate lightweight update repository.
- During early testing, it can point directly to the source repository created in step 1.
- When using a separate update repository, also change the sync targets in `.github/workflows/build.yml` and configure the required GitHub Actions secrets. Remove template-specific CNB or MirrorChyan steps that you do not use.

### 6. Create and Register the First Task

Create a task class under `src/tasks`, then register it in `onetime_tasks` or `trigger_tasks` in `src/config.py`:

```python
'onetime_tasks': [
    ["src.tasks.MyFirstTask", "MyFirstTask"],
    ["ok", "DiagnosisTask"],
],
```

One-time tasks inherit from `BaseTask`; background trigger tasks inherit from `TriggerTask`. Start from `src/tasks/MyOneTimeTask.py`, or ask an AI tool to use `$ok-script-tasks` and `$ok-script-codegen`.

Start in Debug mode to verify the configuration and task:

```bash
python main_debug.py
```

Run tests:

```bash
python -m unittest tests.TestMain
```

### 7. Push a Tag to Build the exe

Commit and push the code, then create a version tag matching the `v*` workflow rule:

```bash
git add .
git commit -m "Initialize project"
git push origin HEAD
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions runs the tests, packages the exe, and creates the matching GitHub Release.

## Project Layout

```text
src/tasks              Sample task classes
src/config.py          ok-script app configuration
src/ui                 Custom UI tab example
tests                  Automated tests
assets                 Template matching assets and COCO annotations
docs/images            Demo images used by the README
i18n                   Localization files
icons                  App icons
.agents/skills         AI initialization, task, i18n, and release skills
main.py                Normal entry point
main_debug.py          Debug entry point
requirements.in        Direct dependency list
requirements.txt       Locked dependency set
run_tests.ps1          PowerShell test entry point
pyappify.yml           Packaging configuration
deploy.txt             File list synced to the update repository during release
.github/workflows      Build and release workflows
```

## Developing Tasks

The one-time task example is in `src/tasks/MyOneTimeTask.py`; the background trigger example is in `src/tasks/MyTriggerTask.py`. Start there to:

- Add default task settings in `default_config`.
- Choose config widget types in `config_type`.
- Write automation logic in `run()`.
- Use `self.ocr()` for text recognition.
- Use `self.find_one()` or `self.find_feature()` for template matching.
- Use `self.info_set()` to show task state in the UI.
- Use `self.log_info(..., notify=True)` to send notifications.

With custom tasks enabled, you can also create and edit task scripts from the GUI.

## Release Files

- `.github/workflows/build.yml`: Watches `v*` tags, runs tests, packages the app, and creates a GitHub Release.
- `pyappify.yml`: Defines the app name, entry point, icon, Python version, and update repositories.
- `deploy.txt`: Lists files synced to the update repository (for future dedicated update repo).

## ok-script Documentation (Chinese)

- [Intro to game automation](https://github.com/ok-oldking/ok-script/blob/master/docs/intro_to_automation/README.md)
- [Quick start](https://github.com/ok-oldking/ok-script/blob/master/docs/quick_start/README.md)
- [After quick start](https://github.com/ok-oldking/ok-script/blob/master/docs/after_quick_start/README.md)
- [API docs](https://github.com/ok-oldking/ok-script/blob/master/docs/api_doc/README.md)

## Community

- Project page: [https://github.com/konghui111/konghuiww](https://github.com/konghui111/konghuiww)

## Credits

- [ok-script](https://github.com/ok-oldking/ok-script)
- [OnnxOCR](https://github.com/ok-oldking/OnnxOCR)
- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
