# BrowseMe v1.3 20250422.09:32
import sys
import os
import argparse
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
import logger_browseme
from logger_browseme import log_error, log_debug

DEFAULT_HOME_URL = 'https://www.duckduckgo.com'
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.3"

class HttpsWebEnginePage(QWebEnginePage):
    def __init__(self, main_window=None, parent=None):
        super(HttpsWebEnginePage, self).__init__(parent)
        self.main_window = main_window
        log_debug("HttpsWebEnginePage initialized")
    
    def acceptNavigationRequest(self, url, _type, isMainFrame):
        try:
            if url.scheme() not in ['https', 'file']:
                log_debug("Non-https or non-file URL blocked: " + url.toString())
                return False
            return super(HttpsWebEnginePage, self).acceptNavigationRequest(url, _type, isMainFrame)
        except Exception as e:
            log_error("Error in acceptNavigationRequest: " + str(e))
            return False

    def createWindow(self, windowType):
        log_debug("createWindow called with type: " + str(windowType))
        if self.main_window is not None:
            self.main_window.add_new_tab()
            return self.main_window.current_browser().page()
        return None

class BrowserTab(QWidget):
    title_changed = pyqtSignal(str)
    
    def __init__(self, main_window, url=None):
        super(BrowserTab, self).__init__()
        self.main_window = main_window
        self.browser = QWebEngineView()
        
        self.browser.setPage(HttpsWebEnginePage(main_window, self.browser))
        self.setup_browser_settings()
        if url:
            self.browser.setUrl(QUrl(url))
        else:
            self.browser.setUrl(QUrl(DEFAULT_HOME_URL))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)
        self.setLayout(layout)
        
        self.browser.page().titleChanged.connect(self.update_title)
        self.browser.urlChanged.connect(self.notify_url_change)
    
    def setup_browser_settings(self):
        self.browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.browser.page().profile().setHttpUserAgent(USER_AGENT)
        self.browser.settings().setAttribute(QWebEngineSettings.AutoLoadImages, True)
    
    def update_title(self, title):
        self.title_changed.emit(title[:10])
    
    def notify_url_change(self, url):
        self.title_changed.emit(url.toString())

class CloseableTab(QWidget):
    def __init__(self, title, close_callback):
        super(CloseableTab, self).__init__()
        self.layout = QHBoxLayout()
        self.label = QLabel(title)
        self.close_button = QPushButton("X")
        self.close_button.setStyleSheet("padding: 3px; margin-top: 10px; margin-right: 20px; margin-bottom: 5px;")

        self.close_button.clicked.connect(close_callback)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.close_button)
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
    
    def update_title(self, title):
        self.label.setText(title)

class MainWindow(QMainWindow):
    def __init__(self, url=None):
        super(MainWindow, self).__init__()
        log_debug("MainWindow initialized")
        self.setWindowIcon(QIcon("/home/coder/bin/Python/BrowseMe/browse-me_icon.png"))
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.tabBar().setStyleSheet("QTabBar::tab {border: 0px; margin-left: 5px; margin-top:3px; margin-right:5px; padding-left:10px;}")

        self.add_new_tab(url or DEFAULT_HOME_URL)
        self.setup_navbar()
        self.setStyleSheet("background-color: #353535; color: white;")
        self.resize(1250, 850)
        self.show()
    
    def setup_navbar(self):
        navbar = QToolBar()
        navbar.setStyleSheet("background-color: black; color: white")
        self.addToolBar(navbar)
        
        open_file_btn = QAction('Open File', self)
        open_file_btn.triggered.connect(self.open_file)
        navbar.addAction(open_file_btn)
        
        new_tab_btn = QAction('New Tab', self)
        new_tab_btn.triggered.connect(lambda: self.add_new_tab())
        navbar.addAction(new_tab_btn)
        
        # removed New Window button, wasn't needed and caused clutter
        # new_window_btn = QAction('New Window', self)
        # new_window_btn.triggered.connect(self.add_new_window)
        # navbar.addAction(new_window_btn)
        
        back_btn = QAction('Back', self)
        back_btn.triggered.connect(self.back_navigation)
        navbar.addAction(back_btn)
        
        forward_btn = QAction('Forward', self)
        forward_btn.triggered.connect(self.forward_navigation)
        navbar.addAction(forward_btn)
        
        reload_btn = QAction('Reload', self)
        reload_btn.triggered.connect(self.reload_current_tab)
        navbar.addAction(reload_btn)
        
        home_btn = QAction('Home', self)
        home_btn.triggered.connect(self.navigate_home)
        navbar.addAction(home_btn)
        
        self.url_bar = QLineEdit()
        self.url_bar.setStyleSheet("background-color: black; color: white; border: 1px solid grey")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navbar.addWidget(self.url_bar)
        
        self.tabs.currentChanged.connect(lambda index: self.update_url_bar())
        
    def add_new_window(self):
        try:
            new_window = MainWindow()
            new_window.show()
            log_debug("Opened a new window.")
        except Exception as e:
            log_error("Error opening a new window: " + str(e))
            QMessageBox.critical(self, "New Window Error", "Failed to open new window: " + str(e))
    
    def open_file(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Open HTML File", "", "HTML Files (*.html *.htm);;All Files (*)")
            if file_name:
                if not file_name.lower().endswith(('.html', '.htm')):
                    QMessageBox.warning(self, "Invalid File", "Please select a valid HTML file.")
                    return
                file_url = QUrl.fromLocalFile(os.path.abspath(file_name)).toString()
                log_debug("Opening local file: " + file_url)
                self.add_new_tab(file_url)
        except Exception as e:
            log_error("Error opening file: " + str(e))
            QMessageBox.critical(self, "File Open Error", "Failed to open file: " + str(e))
    
    def reload_current_tab(self):
        current_browser = self.current_browser()
        if current_browser:
            current_browser.reload()
    
    def back_navigation(self):
        current_browser = self.current_browser()
        if current_browser:
            current_browser.back()
    
    def forward_navigation(self):
        current_browser = self.current_browser()
        if current_browser:
            current_browser.forward()
    
    def add_new_tab(self, url=''):
        try:
            new_tab = BrowserTab(main_window=self, url=url)
            tab_index = self.tabs.addTab(new_tab, "")
            self.tabs.setCurrentWidget(new_tab)
            
            new_tab.title_changed.connect(lambda title, tab=new_tab: self.on_tab_title_changed(tab, title))
            
            new_tab.browser.urlChanged.connect(lambda url, tab=new_tab: self.on_url_changed(tab, url))
            
            closeable_tab = CloseableTab("", lambda: self.close_tab(new_tab))
            self.tabs.tabBar().setTabButton(tab_index, QTabBar.RightSide, closeable_tab)
        except Exception as e:
            log_error("Error adding new tab: " + str(e))
    
    def on_tab_title_changed(self, tab, title):
        tab_index = self.tabs.indexOf(tab)
        if tab_index != -1:
            self.tabs.setTabText(tab_index, title)

            tab_button = self.tabs.tabBar().tabButton(tab_index, QTabBar.RightSide)
            if tab_button and isinstance(tab_button, CloseableTab):
                tab_button.update_title(title)

            if self.tabs.currentIndex() == tab_index:
                self.update_url_bar()
    
    def on_url_changed(self, tab, url):
        if self.tabs.currentWidget() == tab:
            self.url_bar.setText(url.toString())
            log_debug("URL updated to: " + url.toString())
    
    def close_tab(self, tab):
        index = self.tabs.indexOf(tab)
        if index != -1:
            self.tabs.removeTab(index)
            log_debug(f"Closed tab at index: {index}")
            self.update_url_bar()
    
    def current_browser(self):
        current_tab = self.tabs.currentWidget()
        if current_tab and hasattr(current_tab, 'browser'):
            return current_tab.browser
        return None
    
    def navigate_home(self):
        try:
            browser = self.current_browser()
            if browser:
                browser.setUrl(QUrl(DEFAULT_HOME_URL))
                log_debug("Navigated to home page")
        except Exception as e:
            log_error("Error navigating to home page: " + str(e))
            QMessageBox.critical(self, "Navigation Error", "Failed to navigate to home page: " + str(e))
    
    def navigate_to_url(self):
        try:
            url = self.url_bar.text().strip()
            if not url.startswith(('http://', 'https://', 'file://')):
                url = 'https://' + url
            browser = self.current_browser()
            if browser:
                browser.setUrl(QUrl(url))
                log_debug("Navigated to URL: " + url)
        except Exception as e:
            log_error("Error navigating to URL: " + str(e))
            QMessageBox.critical(self, "Navigation Error", "Failed to navigate to the URL: " + str(e))
    
    def update_url_bar(self):
        try:
            browser = self.current_browser()
            if browser:
                current_url = browser.url().toString()
                self.url_bar.setText(current_url)
                log_debug("Updated URL bar with: " + current_url)
        except Exception as e:
            log_error("Error updating URL bar: " + str(e))
    
    def closeEvent(self, event):
        try:
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                tab.browser.page().profile().cookieStore().deleteAllCookies()
            log_debug("Deleted all cookies on close")
        except Exception as e:
            log_error("Error deleting cookies on close: " + str(e))
        super(MainWindow, self).closeEvent(event)

def main():
    try:
        parser = argparse.ArgumentParser(description='BrowseMe')
        parser.add_argument('--url', help='URL to open')
        parser.add_argument('--file', help='Local system file path to open (.html)', default=None)
        args = parser.parse_args()
        
        url = None
        if args.file:
            file_path = os.path.abspath(args.file)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"The file '{file_path}' does not exist.")
            url = QUrl.fromLocalFile(file_path).toString()
            log_debug(f"Opening local file: {url}")
        elif args.url:
            url = args.url
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            log_debug(f"Opening URL: {url}")
        
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        QApplication.setApplicationName('BrowseMe')
        window = MainWindow(url)
        app.exec_()
    except Exception as e:
        log_error("Error in main: " + str(e))
        QMessageBox.critical(None, "Application Error", "An error occurred: " + str(e))

if __name__ == '__main__':
    main()

