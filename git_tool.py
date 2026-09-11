import os
import subprocess
import threading
import sublime
import sublime_plugin


def find_repo_root(start):
    path = start
    while path and path != os.path.dirname(path):
        if os.path.exists(os.path.join(path, ".git")):
            return path
        path = os.path.dirname(path)
    return None


def repo_root_for_window(window):
    view = window.active_view()
    if view and view.file_name():
        root = find_repo_root(os.path.dirname(view.file_name()))
        if root:
            return root
    for folder in window.folders():
        root = find_repo_root(folder)
        if root:
            return root
    return None


def no_console():
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


def set_status(window, text):
    for view in window.views():
        view.set_status("git_run", text)


def clear_status(window):
    for view in window.views():
        view.erase_status("git_run")


class GitDifftoolDirCommand(sublime_plugin.WindowCommand):
    def run(self, rev=None):
        cwd = repo_root_for_window(self.window)
        if not cwd:
            sublime.status_message("git difftool: no repo found")
            return

        cmd = ["git", "difftool", "-d", "--no-prompt"]
        if rev:
            cmd.append(rev)

        subprocess.Popen(cmd, cwd=cwd, startupinfo=no_console())
        sublime.status_message(" ".join(cmd))


class GitRunCommand(sublime_plugin.WindowCommand):
    running = False
    label = ""

    def run(self, args=None, commands=None):
        cwd = repo_root_for_window(self.window)
        if not cwd:
            sublime.status_message("git: no repo found")
            return

        seq = commands if commands else [args]
        self.running = True
        self.label = "git " + " ".join(seq[0])
        self.animate(0)
        threading.Thread(target=self.worker, args=(seq, cwd)).start()

    def animate(self, i):
        if not self.running:
            return
        set_status(self.window, self.label + "." * (i % 4))
        sublime.set_timeout(lambda: self.animate(i + 1), 250)

    def worker(self, seq, cwd):
        text, code, label = "", 0, ""
        for args in seq:
            cmd = ["git"] + args
            label = " ".join(cmd)
            self.label = label
            try:
                proc = subprocess.Popen(
                    cmd, cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    startupinfo=no_console())
                out, _ = proc.communicate()
                text = out.decode("utf-8", "replace").strip()
                code = proc.returncode
            except Exception as err:
                text, code = str(err), 1

            if code != 0:
                break

        sublime.set_timeout(lambda: self.done(label, text, code), 0)

    def done(self, label, text, code):
        self.running = False
        clear_status(self.window)

        if code == 0:
            last = text.splitlines()[-1] if text else "done"
            sublime.status_message(label + " — " + last)
        else:
            panel = self.window.create_output_panel("git")
            panel.run_command("append",
                              {"characters": label + "\n\n" + (text or "failed")})
            self.window.run_command("show_panel", {"panel": "output.git"})