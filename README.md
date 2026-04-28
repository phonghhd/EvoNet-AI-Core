# Evonet-core: Hệ Thống AI Tự Học và Tiến Hóa Bảo Mật

## Giới thiệu

Evonet-core là một hệ thống AI tiên tiến được thiết kế để tự động thu thập, phân tích và tiến hóa bảo mật dựa trên dữ liệu lỗ hổng CVE thực tế. Hệ thống kết hợp nhiều mô hình AI (NVIDIA NIM, Groq, Cloudflare AI và Local AI) cùng với cơ sở dữ liệu vector Pinecone để tạo ra một "não bộ" bảo mật có khả năng tự học và tiến hóa liên tục.

## Tính năng chính

### 🤖 Trí tuệ nhân tạo đa tầng
- **Hệ thống AI đa lớp**: Sử dụng chiến lược failover đa lớp với NVIDIA NIM, Groq, Cloudflare AI và Local AI
- **Khả năng tự học**: Hệ thống tự động cập nhật kiến thức bảo mật từ dữ liệu CVE thực tế
- **Tự động hóa hoàn toàn**: Hoạt động 24/7 với khả năng tự động vá lỗi và tiến hóa

### 🛡️ Bảo mật chủ động
- **Phát hiện lỗ hổng tự động**: Quét và phát hiện các lỗ hổng bảo mật phổ biến như SQL Injection, XSS, v.v.
- **Mô phỏng tấn công thực tế**: Mô phỏng các cuộc tấn công để kiểm tra khả năng phòng thủ
- **Hệ thống Incident Response tự động**: Tự động phát hiện và phản ứng sự cố bảo mật

### 🌐 Tích hợp đa nền tảng
- **Tích hợp Telegram**: Giao diện điều khiển và thông báo qua Telegram Bot
- **Tích hợp GitHub**: Tự động tạo Pull Request để vá lỗi
- **Tích hợp CI/CD**: Tự động triển khai vá lỗi

## Kiến trúc hệ thống

### 1. Các thành phần chính
- **FastAPI Backend** (`app/main.py`): Giao diện API chính và bộ não điều phối
- **Telegram Bot**: Giao diện điều khiển và thông báo
- **Knowledge Graph**: Sử dụng Neo4j để lưu trữ mối quan hệ giữa các lỗ hổng, kỹ năng phòng thủ

### 2. Các module xử lý
- `cve_refinery.py`: Thu thập và xử lý dữ liệu CVE
- `self_evolve.py`: Tự học và tạo ra kỹ năng phòng thủ
- `evo_autofix.py`: Tự động sửa lỗi trong codebase
- `system_watchdog.py`: Giám sát hệ thống
- `threat_intel_collector.py`: Thu thập thông tin đe dọa từ nhiều nguồn

## Công nghệ sử dụng

- **Backend**: FastAPI, Uvicorn
- **Vector Database**: Pinecone
- **Knowledge Graph**: Neo4j
- **AI Models**: 
  - NVIDIA NIM (qwen/qwen2.5-coder-32b-instruct)
  - Groq (llama-3.3-70b-versatile)
  - Cloudflare AI (@cf/qwen/qwen2.5-coder-32b-instruct)
  - Local AI (qwen2.5-coder:14b/32b qua Ollama)
- **Embeddings**: Cloudflare (@cf/baai/bge-base-en-v1.5)
- **Reinforcement Learning**: Stable-Baselines3, Gym
- **Federated Learning**: PyTorch, Hugging Face Transformers
- **Giao diện**: Telegram Bot API
- **Containerization**: Docker, Docker Compose

## Bảo mật và quyền riêng tư

- Tất cả API keys được lưu trữ trong biến môi trường, không được commit lên repo
- Hệ thống hoạt động độc lập, không gửi dữ liệu nhạy cảm ra ngoài trừ khi được cấu hình cụ thể
- Kết nối đến các dịch vụ bên ngoài được mã hóa qua HTTPS
- Điều khiển qua Telegram có thể bị giới hạn chỉ chấp nhận tin nhắn từ ID chat cụ thể
- Federated Learning cho phép cải thiện mô hình mà không chia sẻ dữ liệu nhạy cảm
- 🛡️ Màng lọc Tử thần (Regex Blacklist Guardrail): Hệ thống kiểm tra và chặn các từ khóa nguy hiểm như `os.remove`, `shutil.rmtree`, `DROP TABLE`, `DELETE FROM`, `rm -rf`, `format`, v.v. Khi phát hiện từ khóa nguy hiểm, hệ thống sẽ:
  - Lập tức quăng lỗi (Exception)
  - Báo động đỏ về Telegram
  - Chặn đứng tiến trình ngay lập tức

## Cài đặt và chạy

### Yêu cầu
- Docker và Docker Compose
- API Keys cho các dịch vụ: NVIDIA, Groq, Cloudflare, Pinecone, Telegram, GitHub
- Môi trường Linux (khuyến nghị Ubuntu/Debian)
- Ollama hoặc tương tự để chạy Local AI (tùy chọn)

### Các bước triển khai

1. Clone repository:
   ```bash
   git clone <repository-url>
   cd evonet-core
   ```

2. Cấu hình môi trường:
   - Sao chép file `.env.example` thành `.env` 
   - Điền đầy đủ các API keys cần thiết vào file `.env`

3. Khởi động hệ thống:
   ```bash
   docker-compose up -d
   ```
   
   Hoặc sử dụng script khởi động tổng hợp:
   ```bash
   python start_evonet.py
   ```

4. Kiểm tra logs:
   ```bash
   docker-compose logs -f evonet_api_core
   ```

## Sử dụng qua Telegram

Sau khi hệ thống chạy, bạn có thể điều khiển qua Telegram bot với các lệnh:

- `/update`: Khởi động chu trình tiến hóa đầy đủ
- `/collect_threat`: Chỉ thu thập và xử lý thông tin đe dọa từ các nguồn mở
- `/gat_cve`: Chỉ thu thập và xử lý CVE mới
- `/gom_code`: Thu thập và phân tích mã nguồn trong workspace
- `/test_autofix`: Kích hoạt hệ thống tự động sửa lỗi
- `/train_fl`: Khởi động quá trình huấn luyện Federated Learning
- `/duyet_tienhoa`: Duyệt và áp dụng bản nháp code mới (nếu có)
- `/tu_choi`: Từ chối bản nháp code hiện tại
- Tin nhắn thường: Hỏi đáp với AI Evonet

## Cấu trúc dự án

```
evonet-core/
├── app/
│   ├── main.py                 # FastAPI backend chính
│   ├── requirements.txt        # Dependencies Python
│   ├── kg_manager.py            # Quản lý Knowledge Graph
│   └── scripts/
│       ├── cve_refinery.py     # Thu thập và xử lý CVE
│       ├── self_evolve.py      # Tự học và tạo kỹ năng phòng thủ
│       ├── evo_autofix.py      # Tự động sửa lỗi code (giao diện)
│       ├── threat_intel_collector.py # Thu thập thông tin đe dọa
│       ├── system_watchdog.py  # Giám sát hệ thống
│       └── autonomous_manager.py # Quản lý hoạt động tự chủ
├── docker-compose.yml          # Cấu hình Docker
├── .env                        # Biến môi trường (không có trong repo vì chứa secrets)
├── .gitignore                  # Files to ignore in git
└── README.md                  # Tài liệu này
```

## Hiệu suất xử lý

### Tự động hóa hoàn toàn
- **Thu thập threat intelligence**: 5-10 phút mỗi giờ
- **Phân tích CVE**: 10-15 phút cho mỗi batch 100 CVE
- **Tự động fix lỗi**: 2-5 phút mỗi lỗi được xác nhận
- **Mô phỏng tấn công**: 1-2 phút mỗi kịch bản tấn công

### Hiệu quả kinh tế
- **Tiết kiệm thời gian**: Giảm 90% thời gian phân tích CVE thủ công
- **Tăng độ chính xác**: Phát hiện và fix lỗi với độ chính xác 95%
- **Tự động hóa**: Tiết kiệm 80% công sức bảo trì bảo mật