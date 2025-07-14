#!/usr/bin/env python3
import os
import http.server
import socketserver
from urllib.parse import unquote
import html
import json
import socket
from email.message import EmailMessage
from email import policy

class UploadHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # Tạo giao diện upload
            html_content = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>File Upload Server</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .upload-area { 
                        border: 2px dashed #007bff; 
                        padding: 30px; 
                        text-align: center; 
                        margin: 20px 0;
                        border-radius: 10px;
                        background: #f8f9fa;
                    }
                    .file-list { margin-top: 20px; }
                    .file-item { 
                        padding: 15px; 
                        border-bottom: 1px solid #eee; 
                        display: flex; 
                        justify-content: space-between;
                        align-items: center;
                    }
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
                </style>
            </head>
            <body>
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
                        html_content += f'''
                        <div class="file-item">
                            <span>📄 {html.escape(file)} <small>({size_str})</small></span>
                            <a href="{html.escape(file)}" download class="download-link">⬇️ Tải về</a>
                        </div>
                        '''
                        file_count += 1
                
                if file_count == 0:
                    html_content += '<div class="file-item"><span>📂 Thư mục trống</span></div>'
                    
            except Exception as e:
                html_content += f'<div class="file-item"><span>❌ Không thể đọc thư mục: {e}</span></div>'
            
            html_content += '''
                        </div>
                    </div>
                </div>
                
                <script>
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
                                    location.reload();
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
                </script>
            </body>
            </html>
            '''
            
            self.wfile.write(html_content.encode('utf-8'))
        else:
            # Serve files normally
            super().do_GET()
    
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
        else:
            self.send_response(404)
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
                        header_part, body_part = part.split(b'\n\n', 1)
                    else:
                        continue
                    
                    # Remove trailing boundary markers
                    if body_part.endswith(b'\r\n'):
                        body_part = body_part[:-2]
                    elif body_part.endswith(b'\n'):
                        body_part = body_part[:-1]
                    
                    # Extract filename
                    header_str = header_part.decode('utf-8', errors='ignore')
                    filename = None
                    
                    for line in header_str.split('\n'):
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
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return "127.0.0.1"

def main():
    PORT = 8000
    
    # Hiển thị thông tin server
    print("🚀 Starting File Upload Server...")
    print(f"📡 Server đang chạy tại port {PORT}")
    print("🌐 Để truy cập từ điện thoại:")
    
    # Lấy IP address
    local_ip = get_local_ip()
    print(f"   http://{local_ip}:{PORT}")
    print(f"   http://localhost:{PORT} (chỉ trên máy tính này)")
    print(f"\n📱 Mở trình duyệt trên điện thoại và nhập: http://{local_ip}:{PORT}")
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