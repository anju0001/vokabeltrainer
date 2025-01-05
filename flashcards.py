#!/usr/bin/python3

import gi
from gtts import gTTS
import os
import json
import random

gi.require_version('Gtk', '3.0')
import time
from gi.repository import Gtk, Pango, GLib, Gdk

import subprocess


CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {"lang": "ru","current_file": "russian_words.txt"}  # Default configuration

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file)


class FlashcardWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Worte lernen")

        self.config = load_config()
        self.lang = self.config.get("lang", "ru")  # Load selected language
        self.current_file = self.config.get("current_file", "russian_words.txt") # Load default word file

        # Set up the window
        self.set_default_size(400, 300)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Create vertical box for menu and content
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.vbox)

        # Apply custom background color using CSS
        self.apply_custom_styles()

        # Create menu bar
        self.create_menu()

        # Create horizontal box for counter labels
        self.counter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.vbox.pack_start(self.counter_box, False, True, 5)

        # Create labels for counters
        self.total_words_label = Gtk.Label()
        self.current_word_label = Gtk.Label()

        # Apply CSS classes to the labels
        self.total_words_label.get_style_context().add_class("font-small")
        self.current_word_label.get_style_context().add_class("font-small")

        # Add labels to counter box with proper alignment
        self.counter_box.pack_start(self.total_words_label, False, False, 10)
        self.counter_box.pack_end(self.current_word_label, False, False, 10)

        # Create the main label for displaying words
        self.label = Gtk.Label()
        self.label.set_justify(Gtk.Justification.CENTER)
        self.label.get_style_context().add_class("font-large")
        self.label.set_line_wrap(True)
        self.label.set_vexpand(True)  # Make label expand to fill space

        # Add the main label to the vbox
        self.vbox.pack_start(self.label, True, True, 0)

        # Create the Text-to-Speech button
        self.tts_button = Gtk.Button(label="🔊 Wort vorlesen")
        self.tts_button.connect("clicked", self.on_tts_button_clicked)
        self.vbox.pack_start(self.tts_button, False, True, 10)

        # Initialize variables
        self.current_word_index = 0
        self.click_count = 0
        self.words = []
        self.last_click_time = 0
        self.click_delay = 0.2
        #self.current_file = 'russian_words.txt'

        # Load words from default file
        self.load_words(self.current_file)

        # Display first word if available
        if self.words:
            self.display_current_word()
            self.update_counters()

        # Connect click event
        self.connect("button-press-event", self.on_click)
        
        # Connect key press event
        self.connect("key-press-event", self.on_key_press)

    def on_key_press(self, widget, event):
        # Check if F2 was pressed
        if event.keyval == Gdk.KEY_F2:
            self.show_search_dialog(None)
            return True
        return False


    def create_menu(self):
        menubar = Gtk.MenuBar()
        self.vbox.pack_start(menubar, False, False, 0)

        # Create File menu
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="Datei")
        file_item.set_submenu(file_menu)

        # Create Load File menu item
        load_item = Gtk.MenuItem(label="Datei öffnen")
        load_item.connect("activate", self.on_load_file)
        file_menu.append(load_item)

        # Add separator
        file_menu.append(Gtk.SeparatorMenuItem())

        # Create Quit menu item
        quit_item = Gtk.MenuItem(label="Beenden")
        quit_item.connect("activate", Gtk.main_quit)
        file_menu.append(quit_item)

        menubar.append(file_item)

        # Add Search menu item before appending file_item
        search_menu = Gtk.Menu()
        search_item = Gtk.MenuItem(label="Suchen")
        search_item.set_submenu(search_menu)

        # Suchen Submenu
        word_item = Gtk.MenuItem(label="Übersetzung F2")
        word_item.connect("activate", self.show_search_dialog)
        search_menu.append(word_item)

        menubar.append(search_item)
        
        # Create Settings menu
        settings_menu = Gtk.Menu()
        settings_item = Gtk.MenuItem(label="Einstellungen")
        settings_item.set_submenu(settings_menu)

        # Language Submenu
        lang_submenu = Gtk.Menu()
        lang_item = Gtk.MenuItem(label="Sprache")
        lang_item.set_submenu(lang_submenu)
        settings_menu.append(lang_item)
        menubar.append(settings_item)

        # Add language options with RadioMenuItem
        self.language_items = []
        group = None  # Initial group is None
        languages = {"ru": "Russisch", "de": "Deutsch", "en": "Englisch"}
        for code, name in languages.items():
            lang_option = Gtk.RadioMenuItem(label=name, group=group)
            group = lang_option  # Update group for subsequent items
            lang_option.connect("toggled", self.on_language_select, code)
            lang_submenu.append(lang_option)
            self.language_items.append((lang_option, code))

        # Ensure the current language is selected
        self.update_language_selection() 

    def on_language_select(self, widget, lang_code):
        self.lang = lang_code
        self.config["lang"] = self.lang  # Update config
        save_config(self.config)  # Save to file
        #print(f"Sprache auf {lang_code} gesetzt")  # Debug message

    def update_language_selection(self):
        for lang_option, code in self.language_items:
            lang_option.set_active(code == self.lang)

    def update_counters(self):
        total_words = len(self.words)
        current_word = self.current_word_index + 1
        self.total_words_label.set_text(f"Gesamt: {total_words}")
        self.current_word_label.set_text(f"Aktuell: {current_word}")

    def apply_custom_styles(self):
        css_provider = Gtk.CssProvider()
        css = """
        window {
            background-color: #F7E6A2;
        }
        .font-small {
            font-family: Sans;
            font-size: 12px;
        }
        .font-large {
            font-family: Sans;
            font-size: 29px;
        }
        """
        css_provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


    def show_search_dialog(self, widget):
        dialog = Gtk.Dialog(
            title="Wortsuche",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_FIND, Gtk.ResponseType.OK
        )
        dialog.set_default_size(300, 100)

        # Create and add the search entry
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        search_entry = Gtk.Entry()
        search_entry.set_placeholder_text("Suche nach einem Wort...")
        search_box.pack_start(search_entry, True, True, 5)


        def on_entry_activate(entry):
            search_term = entry.get_text().strip().lower()
            dialog.response(Gtk.ResponseType.OK)

        search_entry.connect("activate", on_entry_activate)

        # Make the find button the default
        find_button = dialog.get_widget_for_response(Gtk.ResponseType.OK)
        find_button.set_can_default(True)
        find_button.grab_default()


        dialog.get_content_area().pack_start(search_box, True, True, 5)
        dialog.show_all()

        # Handle dialog response
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            search_term = search_entry.get_text().strip().lower()
            self.perform_search(search_term)

        dialog.destroy()

    def perform_search(self, search_term):
        if not search_term:
            return

        # Search in both words and translations
        for index, word in enumerate(self.words):
            if (search_term == word['word'].lower() or
                search_term == word['translation'].lower()):
                # Found a match, jump to this word
                self.current_word_index = index
                self.click_count = 0
                self.display_current_word()
                return

        # If no match found, show an error dialog
        error_dialog = Gtk.MessageDialog(parent=self,
                                       flags=0,
                                       message_type=Gtk.MessageType.INFO,
                                       buttons=Gtk.ButtonsType.OK,
                                       text="Keine Ergebnisse gefunden")
        error_dialog.run()
        error_dialog.destroy()



    def on_load_file(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Datei auswählen",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        # Add filters for text files
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text Dateien")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.config["current_file"] = filename  # Update the config
            save_config(self.config)  # Save to file
            self.current_file = filename
            self.load_words(filename)
            if self.words:
                self.current_word_index = 0
                self.click_count = 0
                self.display_current_word()

        dialog.destroy()

    def load_words(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                self.words = []
                for line in file:
                    parts = line.strip().split(';')
                    if len(parts) >= 2:
                        self.words.append({
                            'word': parts[0],
                            'pronunciation': parts[1],
                            'translation': parts[2] if len(parts) > 2 else ''
                        })
                random.shuffle(self.words)  # Randomly mix the words
            if not self.words:
                self.label.set_text("Error: No words found in file")
            else:
                self.update_counters()
        except FileNotFoundError:
            self.label.set_text(f"Error: File {filename} not found")
        except Exception as e:
            self.label.set_text(f"Error loading words: {str(e)}")

    def display_current_word(self):
        if 0 <= self.current_word_index < len(self.words):
            current_word = self.words[self.current_word_index]

            if self.click_count == 0:
                text = current_word['word']
                GLib.idle_add(self.update_counters)
                self.tts_button.set_visible(True)
            elif self.click_count == 1:
                text = f"{current_word['word']}\n\n{current_word['pronunciation']}"
                self.tts_button.set_visible(False)
            elif self.click_count == 2:
                self.tts_button.set_visible(False)
                text = f"{current_word['word']}\n\n{current_word['pronunciation']}\n\n{current_word['translation']}"
                self.click_count = -1
                self.current_word_index = (self.current_word_index + 1) % len(self.words)

            self.label.set_text(text)

    def on_click(self, widget, event):
        if event.y < 30:
            return False

        if not self.words:
            return False

        current_time = time.time()
        if current_time - self.last_click_time < self.click_delay:
            return False
        self.last_click_time = current_time

        self.click_count += 1
        if self.click_count > 2:
            self.click_count = 0

        GLib.idle_add(self.display_current_word)
        return True


    def on_tts_button_clicked(self, widget):
        if self.click_count != 0:
            return
        if 0 <= self.current_word_index < len(self.words):
            current_word = self.words[self.current_word_index]['word']
            tts = gTTS(current_word, lang=self.lang)
            tts.save("current_word.mp3")
        
        # Play the stereo file
            subprocess.run(["mpg321", "current_word.mp3", "--stereo"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    win = FlashcardWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()

