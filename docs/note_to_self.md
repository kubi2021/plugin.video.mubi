## Development Setup 🛠️

Follow these steps to set up your Kodi development environment, so that changes to the plugin code are automatically reflected without needing to reinstall or copy files:

### 1. Install the Plugin from Zip

1. First, **package your plugin** into a `.zip` file.
2. Open Kodi and navigate to **Add-ons** > **Install from zip file**.
3. Select your `.zip` file and install the plugin. This registers the plugin in Kodi.

### 2. Shutdown Kodi ⏹️

Once the plugin is installed, completely **close Kodi**.

### 3. Remove the Installed Plugin Folder

After closing Kodi, navigate to Kodi's **addons** directory, and **remove** the installed plugin folder. This is typically located at:

```bash
~/Library/Application Support/Kodi/addons/plugin.video.mubi
```

Use the following command to remove the folder:

```bash
rm -rf ~/Library/Application\ Support/Kodi/addons/plugin.video.mubi
```

### 4. Create a Symlink to Your Development Folder 🔗

Now, create a **symbolic link (symlink)** from your development folder to the Kodi addons directory. Note that since the repository was restructured into a Kodi repository format, the actual plugin is now located in the `repo/plugin_video_mubi/` subfolder:

```bash
ln -s <path_to_your_dev_folder>/repo/plugin_video_mubi ~/Library/Application\ Support/Kodi/addons/plugin.video.mubi
```

For example:

```bash
ln -s /Users/kubi/Documents/GitHub/plugin.video.mubi/repo/plugin_video_mubi ~/Library/Application\ Support/Kodi/addons/plugin.video.mubi
```

### 5. Restart Kodi 🔄

Once the symlink is created, **restart Kodi**. The plugin will now load directly from your development folder, and any changes made will be automatically reflected in Kodi without needing to reinstall the plugin.