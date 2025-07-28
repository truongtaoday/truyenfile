#!/usr/bin/env python3
import os
import http.server
import socketserver
from urllib.parse import unquote, parse_qs
import html
import json
import socket
import threading
import time
from email.utils import formatdate

# --- Chat Storage ---
# Danh sách lưu trữ tin nhắn chat (trong bộ nhớ)
chat_messages = []
# Khóa để đảm bảo an toàn khi nhiều luồng truy cập chat_messages
chat_lock = threading.Lock()
# --- End Chat Storage ---

class UploadHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve static files (like CSS, JS, images) from the current directory
        if self.path.startswith('/static/') or os.path.isfile(self.path[1:]):
             # Check if the requested file exists in the current directory
             requested_file = self.path[1:] # Remove leading '/'
             if os.path.isfile(requested_file) and not requested_file.startswith('.'):
                  # Use SimpleHTTPRequestHandler's default behavior for files
                  super().do_GET()
                  return
             else:
                  # File not found or access denied
                  self.send_response(404)
                  self.end_headers()
                  self.wfile.write(b'File not found')
                  return

        if self.path == '/' or self.path == '/upload':
            self.serve_upload_page()
        elif self.path == '/chat':
            self.serve_chat_page()
        elif self.path.startswith('/get_messages'):
            self.serve_get_messages()
        else:
            # Serve files normally (fallback)
            super().do_GET()

    def serve_upload_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        # Tạo giao diện upload
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>File Upload & Chat Server</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .nav { background: #007bff; padding: 15px; text-align: center; }
                .nav a { color: white; text-decoration: none; padding: 10px 20px; margin: 0 10px; border-radius: 5px; background: rgba(255,255,255,0.2); }
                .nav a:hover { background: rgba(255,255,255,0.3); }
                .upload-area {
                    border: 2px dashed #007bff;
                    padding: 30px;
                    text-align: center;
                    margin: 20px 0;
                    border-radius: 10px;
                    background: #f8f9fa;
                }
                .file-list { margin-top: 20px; max-height: 400px; overflow-y: auto; border: 1px solid #eee; border-radius: 5px; }
                .file-item {
                    padding: 15px;
                    border-bottom: 1px solid #eee;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .file-item:last-child { border-bottom: none; }
                .upload-btn {
                    padding: 12px 25px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    margin: 10px;
                }
                .upload-btn:hover { background: #0056b3; }
                .upload-btn:disabled { background: #6c757d; cursor: not-allowed; }
                .progress {
                    width: 100%;
                    height: 25px;
                    background: #e9ecef;
                    border-radius: 15px;
                    overflow: hidden;
                    margin: 15px 0;
                    display: none;
                }
                .progress-bar {
                    height: 100%;
                    background: linear-gradient(90deg, #28a745, #20c997);
                    transition: width 0.3s;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                }
                .file-input {
                    padding: 10px;
                    border: 2px solid #ced4da;
                    border-radius: 5px;
                    margin: 10px;
                    width: 100%;
                    max-width: 400px;
                }
                .status {
                    margin: 15px 0;
                    padding: 10px;
                    border-radius: 5px;
                    text-align: center;
                    font-weight: bold;
                }
                .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
                .download-link {
                    color: #007bff;
                    text-decoration: none;
                    padding: 5px 10px;
                    border: 1px solid #007bff;
                    border-radius: 3px;
                    font-size: 14px;
                }
                .download-link:hover { background: #007bff; color: white; }
                h1 { color: #343a40; text-align: center; }
                h3 { color: #495057; }
                /* Chat Styles */
                 .chat-container {
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    padding: 15px;
                    margin-top: 20px;
                    background: #f9f9f9;
                    max-height: 400px;
                    overflow-y: auto;
                }
                .message { margin-bottom: 10px; padding: 8px 12px; border-radius: 10px; max-width: 80%; word-wrap: break-word; }
                .sent { background: #dcf8c6; margin-left: auto; text-align: right; }
                .received { background: #e5e5ea; margin-right: auto; }
                .message-input-container { display: flex; margin-top: 10px; }
                .message-input { flex-grow: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-right: 10px; }
                .send-btn { padding: 10px 15px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
                .send-btn:hover { background: #0056b3; }
                .send-btn:disabled { background: #6c757d; cursor: not-allowed; }
                .chat-status { font-size: 14px; color: #666; text-align: center; margin-top: 10px; }
                /* End Chat Styles */
            </style>
        </head>
        <body>
            <div class="nav">
                <a href="/upload">📁 Upload Files</a>
                <a href="/chat">💬 Chat</a>
            </div>
            <div class="container">
                <h1>📁 File Upload Server</h1>
                <div class="upload-area">
                    <h3>📤 Tải file lên từ điện thoại</h3>
                    <p>Chọn một hoặc nhiều file để upload</p>
                    <form id="uploadForm" enctype="multipart/form-data">
                        <input type="file" id="fileInput" name="files" multiple class="file-input">
                        <br>
                        <button type="submit" class="upload-btn" id="uploadBtn">
                            🚀 Upload Files
                        </button>
                    </form>
                    <div class="progress" id="progressContainer">
                        <div class="progress-bar" id="progressBar">0%</div>
                    </div>
                    <div id="status"></div>
                </div>
                <div class="file-list">
                    <h3>📂 Files trong thư mục hiện tại:</h3>
                    <div id="fileList">
        '''
        # Hiển thị danh sách file
        try:
            files = os.listdir('.')
            file_count = 0
            for file in sorted(files):
                if os.path.isfile(file) and not file.startswith('.'):
                    file_size = os.path.getsize(file)
                    size_str = self.format_file_size(file_size)
                    # Escape HTML to prevent XSS
                    escaped_file = html.escape(file)
                    html_content += f'''
                    <div class="file-item">
                        <span>📄 {escaped_file} <small>({size_str})</small></span>
                        <a href="{escaped_file}" download class="download-link">⬇️ Tải về</a>
                    </div>
                    '''
                    file_count += 1
            if file_count == 0:
                html_content += '<div class="file-item"><span>📂 Thư mục trống</span></div>'
        except Exception as e:
            html_content += f'<div class="file-item"><span>❌ Không thể đọc thư mục: {html.escape(str(e))}</span></div>'
        html_content += '''
                    </div>
                </div>
                <!-- Chat Section -->
                <div class="chat-container">
                    <h3>💬 Chat</h3>
                    <div id="chatMessages"></div>
                    <div class="message-input-container">
                        <input type="text" id="messageInput" class="message-input" placeholder="Nhập tin nhắn..." maxlength="500">
                        <button id="sendButton" class="send-btn">Gửi</button>
                    </div>
                    <div id="chatStatus" class="chat-status">Đang kết nối...</div>
                </div>
                <!-- End Chat Section -->
            </div>
            <script>
            // --- Upload JS ---
            document.getElementById('uploadForm').addEventListener('submit', function(e) {
                e.preventDefault();
                const fileInput = document.getElementById('fileInput');
                const files = fileInput.files;
                const uploadBtn = document.getElementById('uploadBtn');
                if (files.length === 0) {
                    showStatus('⚠️ Vui lòng chọn file!', 'error');
                    return;
                }
                const formData = new FormData();
                for (let i = 0; i < files.length; i++) {
                    formData.append('files', files[i]);
                }
                const progressContainer = document.getElementById('progressContainer');
                const progressBar = document.getElementById('progressBar');
                // Disable button và hiển thị progress
                uploadBtn.disabled = true;
                uploadBtn.textContent = '⏳ Đang upload...';
                progressContainer.style.display = 'block';
                showStatus('📤 Đang upload file...', 'info');
                const xhr = new XMLHttpRequest();
                xhr.upload.addEventListener('progress', function(e) {
                    if (e.lengthComputable) {
                        const percentComplete = Math.round((e.loaded / e.total) * 100);
                        progressBar.style.width = percentComplete + '%';
                        progressBar.textContent = percentComplete + '%';
                    }
                });
                xhr.addEventListener('load', function() {
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = '🚀 Upload Files';
                    if (xhr.status === 200) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            showStatus('✅ ' + response.message, 'success');
                            setTimeout(() => {
                                location.reload(); // Reload để cập nhật danh sách file
                            }, 2000);
                        } catch (e) {
                            showStatus('✅ Upload thành công!', 'success');
                            setTimeout(() => {
                                location.reload();
                            }, 2000);
                        }
                    } else {
                        showStatus('❌ Upload thất bại! Status: ' + xhr.status, 'error');
                    }
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                        progressBar.style.width = '0%';
                        progressBar.textContent = '0%';
                    }, 3000);
                });
                xhr.addEventListener('error', function() {
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = '🚀 Upload Files';
                    showStatus('❌ Có lỗi xảy ra khi upload!', 'error');
                    progressContainer.style.display = 'none';
                });
                xhr.open('POST', '/upload');
                xhr.send(formData);
            });
            function showStatus(message, type) {
                const status = document.getElementById('status');
                status.innerHTML = '<div class="status ' + type + '">' + message + '</div>';
            }
            // Drag and drop support
            const uploadArea = document.querySelector('.upload-area');
            const fileInput = document.getElementById('fileInput');
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, preventDefaults, false);
            });
            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }
            ['dragenter', 'dragover'].forEach(eventName => {
                uploadArea.addEventListener(eventName, highlight, false);
            });
            ['dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, unhighlight, false);
            });
            function highlight(e) {
                uploadArea.style.borderColor = '#0056b3';
                uploadArea.style.backgroundColor = '#e3f2fd';
            }
            function unhighlight(e) {
                uploadArea.style.borderColor = '#007bff';
                uploadArea.style.backgroundColor = '#f8f9fa';
            }
            uploadArea.addEventListener('drop', handleDrop, false);
            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;
                fileInput.files = files;
            }
            // --- End Upload JS ---
            // --- Chat JS ---
            let lastMessageIndex = -1; // Theo dõi tin nhắn mới nhất đã nhận
            let isPolling = false;
            const chatMessagesDiv = document.getElementById('chatMessages');
            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const chatStatusDiv = document.getElementById('chatStatus');

            function updateChatStatus(message) {
                chatStatusDiv.textContent = message;
            }

            function scrollToBottom() {
                chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
            }

            function displayMessages(messages) {
                let needsScroll = false;
                if (chatMessagesDiv.scrollTop + chatMessagesDiv.clientHeight >= chatMessagesDiv.scrollHeight - 5) {
                     needsScroll = true; // Chỉ cuộn xuống nếu đang ở cuối
                }
                messages.forEach(msg => {
                     const messageElement = document.createElement('div');
                     messageElement.classList.add('message');
                     // Giả định sender là 'self' hoặc 'other' dựa trên logic phía server nếu có
                     // Ở đây đơn giản hóa, tất cả đều là received trừ khi có logic khác
                     messageElement.classList.add(msg.sender === 'self' ? 'sent' : 'received');
                     messageElement.textContent = `${msg.text} (${msg.timestamp})`;
                     chatMessagesDiv.appendChild(messageElement);
                });
                if (needsScroll) {
                     scrollToBottom();
                }
            }

            function fetchMessages() {
                if (isPolling) return; // Tránh gọi nhiều lần cùng lúc
                isPolling = true;
                // updateChatStatus("Đang lấy tin nhắn...");
                const xhr = new XMLHttpRequest();
                xhr.open('GET', `/get_messages?last_index=${lastMessageIndex}`, true); // Gửi index cuối cùng
                xhr.onload = function() {
                    isPolling = false;
                    if (xhr.status === 200) {
                        try {
                            const data = JSON.parse(xhr.responseText);
                            if (data.messages && data.messages.length > 0) {
                                displayMessages(data.messages);
                                lastMessageIndex = data.last_index; // Cập nhật index
                            }
                            updateChatStatus(""); // Xóa trạng thái nếu thành công
                        } catch (e) {
                            console.error('Lỗi phân tích JSON tin nhắn:', e);
                            updateChatStatus("Lỗi nhận tin nhắn.");
                        }
                    } else {
                        console.error('Lỗi lấy tin nhắn:', xhr.status);
                        updateChatStatus("Lỗi kết nối (" + xhr.status + ").");
                    }
                    // Lên lịch lấy tin nhắn tiếp theo sau một khoảng thời gian ngắn
                    setTimeout(fetchMessages, 3000); // Poll mỗi 3 giây thay vì 2s để giảm tải
                };
                xhr.onerror = function() {
                    isPolling = false;
                    console.error('Lỗi mạng khi lấy tin nhắn.');
                    updateChatStatus("Lỗi mạng.");
                    setTimeout(fetchMessages, 5000); // Thử lại sau 5s nếu lỗi
                };
                xhr.ontimeout = function() {
                     isPolling = false;
                     console.error('Timeout khi lấy tin nhắn.');
                     updateChatStatus("Timeout kết nối.");
                     setTimeout(fetchMessages, 5000);
                };
                xhr.timeout = 10000; // Timeout 10 giây
                xhr.send();
            }

            function sendMessage() {
                const messageText = messageInput.value.trim();
                if (!messageText) return;
                const originalText = messageInput.value; // Lưu lại để đặt lại nếu cần
                messageInput.value = '';
                sendButton.disabled = true;
                updateChatStatus("Đang gửi...");
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/send_message', true);
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                xhr.onload = function() {
                    sendButton.disabled = false;
                    if (xhr.status === 200) {
                         updateChatStatus("");
                         // Tin nhắn sẽ được hiển thị khi polling tiếp theo
                    } else {
                        console.error('Lỗi gửi tin nhắn:', xhr.status);
                        messageInput.value = originalText; // Đặt lại nội dung
                        updateChatStatus("Gửi thất bại (" + xhr.status + ").");
                    }
                };
                xhr.onerror = function() {
                    sendButton.disabled = false;
                    console.error('Lỗi mạng khi gửi tin nhắn.');
                    messageInput.value = originalText;
                    updateChatStatus("Lỗi mạng khi gửi.");
                };
                xhr.ontimeout = function() {
                     sendButton.disabled = false;
                     console.error('Timeout khi gửi tin nhắn.');
                     messageInput.value = originalText;
                     updateChatStatus("Timeout gửi tin nhắn.");
                };
                xhr.timeout = 10000; // Timeout 10 giây
                // Gửi tin nhắn dưới dạng x-www-form-urlencoded
                xhr.send(`message=${encodeURIComponent(messageText)}`);
            }

            sendButton.addEventListener('click', sendMessage);
            messageInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });

            // Bắt đầu polling khi trang tải xong
             window.addEventListener('load', function() {
                 fetchMessages(); // Bắt đầu lấy tin nhắn ngay lập tức
             });
            // --- End Chat JS ---
            </script>
        </body>
        </html>
        '''
        self.wfile.write(html_content.encode('utf-8'))

    def serve_chat_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        # Tạo giao diện chat
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>File Upload & Chat Server - Chat</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .nav { background: #007bff; padding: 15px; text-align: center; }
                .nav a { color: white; text-decoration: none; padding: 10px 20px; margin: 0 10px; border-radius: 5px; background: rgba(255,255,255,0.2); }
                .nav a:hover { background: rgba(255,255,255,0.3); }
                h1 { color: #343a40; text-align: center; }
                h3 { color: #495057; }
                /* Chat Styles */
                 .chat-container {
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    padding: 15px;
                    margin-top: 20px;
                    background: #f9f9f9;
                    max-height: 70vh; /* Chiều cao cố định cho khung chat */
                    display: flex;
                    flex-direction: column;
                }
                #chatMessages {
                    flex-grow: 1;
                    overflow-y: auto; /* Cuộn dọc nếu tin nhắn nhiều */
                    padding: 10px;
                    border: 1px solid #eee;
                    border-radius: 5px;
                    background: white;
                    margin-bottom: 15px;
                }
                .message { margin-bottom: 10px; padding: 10px 15px; border-radius: 15px; max-width: 70%; word-wrap: break-word; }
                .sent { background: #dcf8c6; margin-left: auto; text-align: right; }
                .received { background: #e5e5ea; margin-right: auto; }
                .message-input-container { display: flex; }
                .message-input { flex-grow: 1; padding: 12px; border: 1px solid #ccc; border-radius: 20px; margin-right: 10px; }
                .send-btn { padding: 12px 20px; background: #007bff; color: white; border: none; border-radius: 20px; cursor: pointer; }
                .send-btn:hover { background: #0056b3; }
                .send-btn:disabled { background: #6c757d; cursor: not-allowed; }
                .chat-status { font-size: 14px; color: #666; text-align: center; margin-top: 10px; }
                /* End Chat Styles */
            </style>
        </head>
        <body>
            <div class="nav">
                <a href="/upload">📁 Upload Files</a>
                <a href="/chat">💬 Chat</a>
            </div>
            <div class="container">
                <h1>💬 Chat Room</h1>
                <!-- Chat Section -->
                <div class="chat-container">
                    <div id="chatMessages"></div>
                    <div class="message-input-container">
                        <input type="text" id="messageInput" class="message-input" placeholder="Nhập tin nhắn..." maxlength="500">
                        <button id="sendButton" class="send-btn">Gửi</button>
                    </div>
                    <div id="chatStatus" class="chat-status">Đang kết nối...</div>
                </div>
                <!-- End Chat Section -->
            </div>
            <script>
            // --- Chat JS (Giống như phần chat trong trang upload) ---
            let lastMessageIndex = -1; // Theo dõi tin nhắn mới nhất đã nhận
            let isPolling = false;
            const chatMessagesDiv = document.getElementById('chatMessages');
            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const chatStatusDiv = document.getElementById('chatStatus');

            function updateChatStatus(message) {
                chatStatusDiv.textContent = message;
            }

            function scrollToBottom() {
                chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
            }

             function displayMessages(messages) {
                let needsScroll = false;
                if (chatMessagesDiv.scrollTop + chatMessagesDiv.clientHeight >= chatMessagesDiv.scrollHeight - 5) {
                     needsScroll = true; // Chỉ cuộn xuống nếu đang ở cuối
                }
                messages.forEach(msg => {
                     const messageElement = document.createElement('div');
                     messageElement.classList.add('message');
                     // Giả định server trả về sender: 'self' hoặc 'other'
                     messageElement.classList.add(msg.sender === 'self' ? 'sent' : 'received');
                     messageElement.textContent = `${msg.text} (${msg.timestamp})`;
                     chatMessagesDiv.appendChild(messageElement);
                });
                if (needsScroll) {
                     scrollToBottom();
                }
            }


            function fetchMessages() {
                if (isPolling) return; // Tránh gọi nhiều lần cùng lúc
                isPolling = true;
                // updateChatStatus("Đang lấy tin nhắn...");
                const xhr = new XMLHttpRequest();
                xhr.open('GET', `/get_messages?last_index=${lastMessageIndex}`, true); // Gửi index cuối cùng
                xhr.onload = function() {
                    isPolling = false;
                    if (xhr.status === 200) {
                        try {
                            const data = JSON.parse(xhr.responseText);
                            if (data.messages && data.messages.length > 0) {
                                displayMessages(data.messages);
                                lastMessageIndex = data.last_index; // Cập nhật index
                            }
                            // updateChatStatus(""); // Xóa trạng thái nếu thành công
                        } catch (e) {
                            console.error('Lỗi phân tích JSON tin nhắn:', e);
                            updateChatStatus("Lỗi nhận tin nhắn.");
                        }
                    } else {
                        console.error('Lỗi lấy tin nhắn:', xhr.status);
                         updateChatStatus("Lỗi kết nối (" + xhr.status + ").");
                    }
                    // Lên lịch lấy tin nhắn tiếp theo sau một khoảng thời gian ngắn
                    setTimeout(fetchMessages, 3000); // Poll mỗi 3 giây
                };
                xhr.onerror = function() {
                    isPolling = false;
                    console.error('Lỗi mạng khi lấy tin nhắn.');
                    updateChatStatus("Lỗi mạng.");
                    setTimeout(fetchMessages, 5000); // Thử lại sau 5s nếu lỗi
                };
                 xhr.ontimeout = function() {
                     isPolling = false;
                     console.error('Timeout khi lấy tin nhắn.');
                     updateChatStatus("Timeout kết nối.");
                     setTimeout(fetchMessages, 5000);
                };
                xhr.timeout = 10000; // Timeout 10 giây
                xhr.send();
            }

            function sendMessage() {
                const messageText = messageInput.value.trim();
                if (!messageText) return;
                const originalText = messageInput.value; // Lưu lại để đặt lại nếu cần
                messageInput.value = '';
                sendButton.disabled = true;
                updateChatStatus("Đang gửi...");
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/send_message', true);
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                xhr.onload = function() {
                    sendButton.disabled = false;
                    if (xhr.status === 200) {
                         updateChatStatus("");
                         // Tin nhắn sẽ được hiển thị khi polling tiếp theo
                    } else {
                        console.error('Lỗi gửi tin nhắn:', xhr.status);
                        messageInput.value = originalText; // Đặt lại nội dung
                        updateChatStatus("Gửi thất bại (" + xhr.status + ").");
                    }
                };
                xhr.onerror = function() {
                    sendButton.disabled = false;
                    console.error('Lỗi mạng khi gửi tin nhắn.');
                    messageInput.value = originalText;
                    updateChatStatus("Lỗi mạng khi gửi.");
                };
                xhr.ontimeout = function() {
                     sendButton.disabled = false;
                     console.error('Timeout khi gửi tin nhắn.');
                     messageInput.value = originalText;
                     updateChatStatus("Timeout gửi tin nhắn.");
                };
                xhr.timeout = 10000; // Timeout 10 giây
                // Gửi tin nhắn dưới dạng x-www-form-urlencoded
                xhr.send(`message=${encodeURIComponent(messageText)}`);
            }

            sendButton.addEventListener('click', sendMessage);
            messageInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });

            // Bắt đầu polling khi trang tải xong
             window.addEventListener('load', function() {
                 fetchMessages(); // Bắt đầu lấy tin nhắn ngay lập tức
             });
            // --- End Chat JS ---
            </script>
        </body>
        </html>
        '''
        self.wfile.write(html_content.encode('utf-8'))

    def serve_get_messages(self):
        """Xử lý yêu cầu GET để lấy tin nhắn mới"""
        try:
            query = self.path.split('?', 1)[1] if '?' in self.path else ''
            params = parse_qs(query)
            last_index_str = params.get('last_index', ['-1'])[0]
            last_index = int(last_index_str)

            # Lấy tin nhắn mới từ last_index trở đi (thread-safe)
            with chat_lock:
                if last_index < 0 or last_index >= len(chat_messages):
                    # Nếu client chưa có tin nhắn nào hoặc index không hợp lệ, gửi tất cả
                    messages_to_send = chat_messages[:]
                    new_last_index = len(chat_messages) - 1 if chat_messages else -1
                else:
                    # Chỉ gửi tin nhắn mới từ last_index + 1
                    messages_to_send = chat_messages[last_index + 1:]
                    new_last_index = len(chat_messages) - 1

            # Gửi response JSON
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            response_data = {
                'messages': messages_to_send,
                'last_index': new_last_index
            }
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

        except (ValueError, IndexError) as e:
            print(f"❌ Lỗi xử lý yêu cầu get_messages: {e}")
            self.send_response(400) # Bad Request
            self.end_headers()
        except Exception as e:
            print(f"❌ Lỗi không xác định trong get_messages: {e}")
            self.send_response(500)
            self.end_headers()


    def do_POST(self):
        if self.path == '/upload':
            try:
                # Đọc content-length
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    raise ValueError("No content to upload")
                # Đọc dữ liệu POST
                post_data = self.rfile.read(content_length)
                # Parse multipart data
                boundary = self.get_boundary()
                if not boundary:
                    raise ValueError("No boundary found in multipart data")
                files = self.parse_multipart(post_data, boundary)
                uploaded_files = []
                for filename, file_data in files:
                    if filename and file_data:
                        # Tạo tên file an toàn
                        safe_filename = os.path.basename(filename)
                        if not safe_filename:
                            continue
                        # Tránh ghi đè file
                        counter = 1
                        original_name = safe_filename
                        while os.path.exists(safe_filename):
                            name, ext = os.path.splitext(original_name)
                            safe_filename = f"{name}_{counter}{ext}"
                            counter += 1
                        # Lưu file
                        with open(safe_filename, 'wb') as f:
                            f.write(file_data)
                        uploaded_files.append(safe_filename)
                        print(f"✅ Đã lưu file: {safe_filename} ({len(file_data)} bytes)")
                # Gửi response thành công
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {
                    'status': 'success',
                    'files': uploaded_files,
                    'message': f'Đã upload thành công {len(uploaded_files)} file(s)!'
                }
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                print(f"❌ Lỗi upload: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                response = {
                    'status': 'error',
                    'message': f'Lỗi upload: {str(e)}'
                }
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        elif self.path == '/send_message':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length).decode('utf-8')
                parsed_data = parse_qs(post_data)
                message_text = parsed_data.get('message', [''])[0]
                if not message_text:
                     self.send_response(400) # Bad Request
                     self.end_headers()
                     return
                # Tạo tin nhắn mới
                new_message = {
                    'text': message_text,
                    'timestamp': time.strftime('%H:%M:%S'), # Dạng giờ:phút:giây
                    'sender': 'other' # Đơn giản hóa, không phân biệt người gửi cụ thể
                }
                # Thêm vào danh sách tin nhắn (thread-safe)
                with chat_lock:
                    chat_messages.append(new_message)
                    # Giới hạn số lượng tin nhắn trong bộ nhớ (tùy chọn)
                    if len(chat_messages) > 100:
                         chat_messages.pop(0) # Xóa tin nhắn cũ nhất nếu quá 100
                print(f"💬 Tin nhắn mới: {message_text}")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'success', 'message': 'Tin nhắn đã được gửi'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                print(f"❌ Lỗi xử lý tin nhắn: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'error', 'message': str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
         # Xử lý preflight request cho CORS (nếu cần)
         self.send_response(200)
         self.send_header('Access-Control-Allow-Origin', '*')
         self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
         self.send_header('Access-Control-Allow-Headers', 'Content-Type')
         self.end_headers()

    def get_boundary(self):
        """Lấy boundary từ Content-Type header"""
        content_type = self.headers.get('Content-Type', '')
        if 'boundary=' in content_type:
            return content_type.split('boundary=')[1].split(';')[0].strip()
        return None

    def parse_multipart(self, data, boundary):
        """Parse multipart form data đơn giản"""
        files = []
        boundary_bytes = ('--' + boundary).encode()
        parts = data.split(boundary_bytes)
        for part in parts:
            if b'Content-Disposition' in part and b'filename=' in part:
                try:
                    # Tách header và body
                    if b'\r\n\r\n' in part:
                        header_part, body_part = part.split(b'\r\n\r\n', 1)
                    elif b'\n\n' in part:
                         # Fallback cho hệ thống dùng LF thay vì CRLF
                        header_part, body_part = part.split(b'\n\n', 1)
                    else:
                        continue # Không tìm thấy phần header/body

                    # Remove trailing boundary markers (e.g., --boundary-- or \r\n)
                    # Tìm vị trí của boundary kết thúc trong body_part
                    end_markers = [b'\r\n--' + boundary_bytes[2:], b'\n--' + boundary_bytes[2:], b'--' + boundary_bytes[2:]]
                    end_pos = len(body_part)
                    for marker in end_markers:
                         pos = body_part.find(marker)
                         if pos != -1 and pos < end_pos:
                              end_pos = pos
                    body_part = body_part[:end_pos]

                    # Extract filename
                    header_str = header_part.decode('utf-8', errors='ignore')
                    filename = None
                    for line in header_str.splitlines(): # Dùng splitlines() để xử lý \r\n và \n
                        if 'filename=' in line:
                            # Extract filename from Content-Disposition header
                            parts = line.split('filename=')
                            if len(parts) > 1:
                                filename = parts[1].strip().strip('"\'')
                                break
                    if filename and body_part:
                        files.append((filename, body_part))
                except Exception as e:
                    print(f"⚠️ Lỗi parse part: {e}")
                    continue
        return files

    def format_file_size(self, size_bytes):
        """Chuyển đổi kích thước file sang dạng dễ đọc"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

def get_local_ip():
    """Lấy IP address của máy"""
    try:
        # Tạo socket để lấy IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Không cần kết nối thực sự, chỉ cần chọn một địa chỉ có thể route
        s.connect(("10.255.255.255", 1)) # Địa chỉ này thường không tồn tại nhưng đủ để chọn interface đúng
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return "127.0.0.1"

def main():
    PORT = 8000
    # Hiển thị thông tin server
    print("🚀 Starting File Upload & Chat Server...")
    print(f"📡 Server đang chạy tại port {PORT}")
    print("🌐 Để truy cập từ điện thoại/máy tính:")
    # Lấy IP address
    local_ip = get_local_ip()
    print(f"   Upload: http://{local_ip}:{PORT}/upload")
    print(f"   Chat:   http://{local_ip}:{PORT}/chat")
    print(f"   Home:   http://{local_ip}:{PORT} (Upload)")
    print(f"   http://localhost:{PORT} (chỉ trên máy tính này)")
    print(f"\n📱 Mở trình duyệt trên thiết bị và nhập các URL trên.")
    print("🛑 Nhấn Ctrl+C để dừng server")
    print("📁 Files sẽ được lưu tại:", os.getcwd())
    print("-" * 60)
    # Tạo và chạy server
    with socketserver.TCPServer(("", PORT), UploadHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server đã dừng!")

if __name__ == "__main__":
    main()
