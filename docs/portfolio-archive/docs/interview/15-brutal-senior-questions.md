# 15 Câu Hỏi Phỏng Vấn Hóc Búa Nhất & Cách Trả Lời Chuẩn Senior
## Dành Cho Ứng Viên Senior Software Engineer / Software Architect / Senior Platform Engineer

Bộ câu hỏi này được tổng hợp từ những câu hỏi "xoay" sâu nhất của các Tech Lead và Principal Engineer khi xem xét một kiến trúc phân tán có xử lý tải cao.

---

### Câu 1: "Tại sao bạn không dùng Distributed Transactions (2PC) mà lại dùng Saga/Outbox?"
**Trả lời:**
> "2PC là giao thức chặn (blocking protocol). Trong pha Prepare, các resource manager phải giữ khóa (lock) dữ liệu. Trong bài toán flash sale với hàng nghìn request/giây, chỉ cần một nút mạng bị trễ 200ms thì toàn bộ các luồng khác sẽ bị block, gây cạn kiệt connection pool và dẫn đến sập dây chuyền (cascading failure). Do đó, tôi chọn Saga kết hợp Transactional Outbox. Chúng tôi đánh đổi tính nhất quán tức thời (ACID) để lấy tính sẵn sàng cao (High Availability) và tính nhất quán sau cùng (Eventual Consistency), dùng giao dịch bù trừ (compensation) nếu có bước thất bại."

---

### Câu 2: "Nếu Redis sập hoặc mất kết nối ngay giữa đợt Flash Sale thì hệ thống xử lý thế nào?"
**Trả lời:**
> "Hệ thống áp dụng kiến trúc Graceful Degradation:
> 1. Redis chỉ đóng vai trò là Fast-Fail Cache / Traffic Shield để giảm tải cho database, nó **không phải** là nơi lưu trữ tồn kho chính thức.
> 2. Nếu Redis không khả dụng, request sẽ đi thẳng xuống tầng Database (PostgreSQL). Tại PostgreSQL, chúng tôi có cơ chế bảo vệ dòng bằng Conditional Update: `UPDATE Products SET AvailableStock = AvailableStock - @qty WHERE Id = @id AND AvailableStock >= @qty`.
> 3. Tốc độ xử lý của hệ thống sẽ bị giảm (latency tăng) để bảo vệ DB thông qua Rate Limiting và Connection Pool giới hạn, nhưng nguyên tắc kinh doanh quan trọng nhất là **không bao giờ bị oversell** vẫn được bảo toàn 100%."

---

### Câu 3: "Làm thế nào bạn chứng minh được hệ thống không bị Oversell dưới tải cao?"
**Trả lời:**
> "Chúng tôi không suy đoán mà chứng minh bằng bài kiểm tra tải thực tế (k6 concurrency harness). Chúng tôi thiết lập 50 Virtual Users (VU) gửi request đặt hàng đồng thời trong 1 giây để tranh chấp một mặt hàng chỉ còn 10 đơn vị tồn kho. Kết quả đo được:
> - Đúng 10 đơn hàng trả về `HTTP 202 Accepted`.
> - 40 đơn hàng trả về `HTTP 409 Out of stock`.
> - Tồn kho ban đầu là 500, sau khi chạy test tồn kho chính xác là 490.
> - Số lượng bán quá tồn kho là **chính xác bằng 0**.
> - P95 response time đạt **132.2 ms**."

---

### Câu 4: "Tại sao bạn khẳng định RPO không thể bằng 0 nếu chỉ dùng pg_dump định kỳ?"
**Trả lời:**
> "Bởi vì `pg_dump` tạo ra một cold snapshot tại thời điểm cố định $T_0$. Nếu thảm họa xảy ra tại $T_1$, mọi giao dịch đã commit với khách hàng trong khoảng thời gian $\Delta T = T_1 - T_0$ đều chưa nằm trong file dump đó. Trong bài diễn tập DR thực tế của chúng tôi (`enterprise_dr_drill_with_delta.sh`), snapshot chụp lúc $T_0$ có 62 đơn hàng; sau đó chúng tôi bơm 5 đơn hàng mới rồi drop database. Sau khi restore snapshot $T_0$, 5 đơn hàng đó bị mất hoàn toàn, tương ứng với RPO = 4 giây. Để đạt RPO = 0 trong ngân hàng, kiến trúc bắt buộc phải có Continuous WAL Archiving (PITR) hoặc Synchronous Database Replication với `synchronous_commit = on`."

---

### Câu 5: "Làm sao đảm bảo một đơn hàng không bị xử lý 2 lần khi Worker đọc message từ Queue?"
**Trả lời:**
> "Trong hệ phân tán, Message Broker (RabbitMQ / Service Bus) chỉ đảm bảo ngữ nghĩa **At-Least-Once Delivery**, không có exactly-once tuyệt đối trên toàn mạng. Vì vậy, Consumer (Worker) bắt buộc phải đạt tính **Idempotent**:
> 1. Mỗi message gửi đi đều mang `idempotency_key` hoặc `message_id`.
> 2. Khi Worker nhận message, nó kiểm tra bảng `InboxMessages` hoặc `ProcessedOrders` trong database.
> 3. Nếu key đã tồn tại và đã được xử lý, Worker chỉ cần ACK message cho broker và bỏ qua việc trừ kho lại lần hai.
> 4. Toàn bộ thao tác ghi nhận đơn hàng và đánh dấu message đã xử lý nằm trong cùng một local database transaction."

---

### Câu 6: "Tại sao Domain và Application layer trong Clean Architecture không được reference EF Core hay Redis?"
**Trả lời:**
> "Theo Dependency Inversion Principle, nghiệp vụ cốt lõi của doanh nghiệp (Domain Rules) phải tồn tại độc lập với công nghệ lưu trữ. EF Core hay Redis chỉ là chi tiết hạ tầng (Infrastructure Details). Nếu Domain phụ thuộc vào EF Core:
> 1. Bạn sẽ không thể viết Unit Test cho business logic thuần túy mà không cần mock hoặc dựng database.
> 2. Việc thay đổi ORM hoặc nâng cấp framework sẽ làm lây lan bug vào logic nghiệp vụ.
> Trong repo của chúng tôi, quy tắc này được kiểm tra bằng Unit Test tự động (`ArchitectureTests.cs`); nếu ai thêm reference từ Domain vào Infrastructure thì test sẽ fail và chặn merge code ngay lập tức."

---

### Câu 7: "Tại sao bạn chọn Kubernetes Gateway API thay vì Nginx Ingress Controller?"
**Trả lời:**
> "Gateway API là bước tiến hóa chuẩn mực của Kubernetes:
> 1. Tách bạch trách nhiệm theo vai trò: Platform Admin sở hữu `Gateway` (cấu hình port, IP, TLS), còn Developer của từng service sở hữu `HTTPRoute` trong namespace của mình.
> 2. Khả năng định tuyến xuyên namespace (Cross-Namespace Routing) an toàn mà không cần lạm dụng vendor-specific annotations.
> 3. Hỗ trợ chuẩn hóa cả HTTP, gRPC, TCP, và UDP trên cùng một chuẩn API. Trong hệ thống của chúng tôi, cả hai workload FlashSale (.NET) và QuanLyKho (Python) đều định tuyến mượt mà qua một Envoy Gateway duy nhất mà không cần cài thêm nhiều Ingress controller riêng lẻ."

---

### Câu 8: "Làm thế nào bạn triển khai CI/CD lên Cloud mà không lưu Secret trong GitHub Repository?"
**Trả lời:**
> "Chúng tôi sử dụng **Workload Identity Federation (Azure OIDC)**:
> 1. GitHub Actions runner yêu cầu một JWT token từ OpenID Connect provider của GitHub.
> 2. Microsoft Entra ID thẩm định token này và đối chiếu với Federated Identity Credential đã đăng ký (khớp chính xác repository và protected environment).
> 3. Entra ID cấp lại một OAuth2 Access Token ngắn hạn có thời hạn 1 giờ.
> 4. Nhờ vậy, trong GitHub Settings không có bất kỳ Client Secret hay mật khẩu nào được lưu trữ, loại bỏ hoàn toàn nguy cơ rò rỉ secret hoặc token hết hạn gây nghẽn pipeline."

---

### Câu 9: "Lỗi Annotation 262KB trong Kubernetes xảy ra khi nào và bạn giải quyết thế nào?"
**Trả lời:**
> "Khi dùng `kubectl apply` kiểu Client-side, Kubernetes sẽ ghi toàn bộ nội dung manifest vào annotation `kubectl.kubernetes.io/last-applied-configuration`. Do giới hạn kích thước metadata của etcd là 262,144 bytes, các file manifest có schema CRD lớn như `applicationsets.argoproj.io` của Argo CD sẽ bị lỗi và văng ra ngoài. Chúng tôi giải quyết bằng cách áp dụng **Server-Side Apply** (`--server-side --force-conflicts`). Cơ chế này lưu trữ field ownership trực tiếp trên API server mà không tạo annotation, cho phép apply các CRD lớn trơn tru."

---

### Câu 10: "Làm thế nào bạn phân quyền chi nhánh trong hệ thống Core Banking / Retail Finance?"
**Trả lời:**
> "Chúng tôi áp dụng mô hình Tenant Isolation cấp ứng dụng:
> 1. Mỗi request từ nhân viên chi nhánh đều chứa JWT token mang claim `outlet_id`.
> 2. Tại tầng Data Access, mọi câu truy vấn số dư quỹ tiền (`cash_boxes`) và tạo bút toán (`journal_entries`) đều tự động chèn mệnh đề `WHERE outlet_id = @user_outlet_id`.
> 3. Được kiểm chứng bằng 31 integration tests chạy trên Testcontainers MySQL 8: một user thuộc chi nhánh A cố tình gửi request can thiệp số dư của chi nhánh B sẽ nhận ngay lỗi `403 Forbidden`."

---

### Câu 11: "Tại sao bạn dùng Testcontainers thay vì mock Database trong Integration Tests?"
**Trả lời:**
> "Mock Database chỉ kiểm tra được logic gọi hàm của code bạn, nhưng không phát hiện được các lỗi nghiêm trọng về cơ sở dữ liệu thật như:
> - Sai cú pháp SQL Dialect giữa PostgreSQL và In-Memory H2.
> - Xung đột Deadlock và hành vi của Transaction Isolation Level (`READ COMMITTED` vs `SERIALIZABLE`).
> - Foreign Key constraints và Unique Index violations dưới concurrency.
> Sử dụng Testcontainers khởi chạy một container Docker PostgreSQL/MySQL thật trong vài giây giúp chúng tôi tự tin 100% rằng code chạy đúng trên engine cơ sở dữ liệu production."

---

### Câu 12: "Bạn xử lý sự cố trôi dạt cấu hình (Configuration Drift) trong Kubernetes như thế nào?"
**Trả lời:**
> "Chúng tôi vận hành theo nguyên lý GitOps với Argo CD:
> 1. Git là nguồn chân lý duy nhất (Single Source of Truth).
> 2. Cấu hình `selfHeal: true` được kích hoạt trên Argo CD Application.
> 3. Nếu ai đó dùng lệnh `kubectl edit` hoặc `kubectl scale` trực tiếp trên cluster, Argo CD controller sẽ phát hiện sự sai lệch giữa Live State và Desired State trong Git và tự động đồng bộ đè lại trạng thái trong Git trong vòng vài giây."

---

### Câu 13: "Sự khác biệt giữa Liveness Probe và Readiness Probe trong kiến trúc microservice là gì?"
**Trả lời:**
> "- **Liveness Probe (`/health/live`):** Kiểm tra xem tiến trình ứng dụng có còn sống hay không. Nếu probe thất bại liên tục (ví dụ bị deadlock luồng hoặc OOM), Kubernetes sẽ **restart container**. Liveness probe không nên kiểm tra database bên ngoài để tránh việc DB sập làm toàn bộ pod bị restart dây chuyền.
> - **Readiness Probe (`/health/ready`):** Kiểm tra xem container đã sẵn sàng phục vụ lưu lượng hay chưa (ví dụ đã kết nối DB thành công, nạp xong cache). Nếu probe thất bại, Kubernetes chỉ **tạm thời ngắt pod khỏi Service Load Balancer** mà không restart container, bảo vệ hệ thống không gửi request vào pod đang chưa sẵn sàng."

---

### Câu 14: "Tại sao trong monorepo bạn cần cấu hình Path Filtering cho CI workflow?"
**Trả lời:**
> "Trong một Monorepo chứa nhiều dịch vụ viết bằng các ngôn ngữ khác nhau (Java, C#, Python, Terraform), nếu mỗi commit nhỏ ở một dịch vụ mà kích hoạt toàn bộ test suite thì:
> - Thời gian CI sẽ kéo dài lên 15–20 phút, gây nghẽn hàng đợi (queue saturation).
> - Lãng phí tài nguyên và chi phí compute của GitHub Actions runner.
> Bằng cách sử dụng `dorny/paths-filter`, chúng tôi chỉ kích hoạt CI cho đúng subsystem bị thay đổi (ví dụ: commit sửa Python chỉ chạy Pytest của QuanLyKho; commit sửa .NET chỉ chạy unit/integration test của OpsBridge)."

---

### Câu 15: "Bạn rút ra bài học gì quan trọng nhất khi xây dựng toàn bộ nền tảng này?"
**Trả lời:**
> "Bài học lớn nhất là: **Evidence-First Engineering (Kỹ thuật dựa trên bằng chứng)**. Không bao giờ đưa ra các tuyên bố chủ quan như 'hệ thống đảm bảo zero downtime' hay 'RPO bằng 0 tuyệt đối' mà không có phép đo thực nghiệm. Một kỹ sư Senior xuất sắc là người hiểu rõ giới hạn của giải pháp mình chọn, luôn đo lường trước và sau khi tối ưu hóa, và thiết kế hệ thống có tính chịu lỗi (fault-tolerant) thay vì chỉ xây dựng cho kịch bản hoàn hảo (happy path)."
