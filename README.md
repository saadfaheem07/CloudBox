CloudBox – Secure Personal Cloud Storage Service

CloudBox is a fully containerized cloud-storage microservice that allows users to securely upload, store, retrieve, and manage files using AWS S3.
The backend is built with Node.js + Express, uses PostgreSQL for file metadata, AWS S3 for object storage, and JWT-based authentication for secure access.
Designed with production-level engineering practices: modular APIs, Dockerized deployment, environment-based configuration, and horizontal scalability.

🚀 Features

🔐 User Authentication – JWT-secured login and protected routes

☁️ AWS S3 File Storage – Upload, download, rename, delete

📁 Folder System – Nested folder creation & organization

🗂️ PostgreSQL Metadata Store – Track file/folder structure & user ownership

🐳 Fully Dockerized – Run the whole system with a single docker-compose up

🧩 Modular Express APIs – Clean controller/service/database layers

📈 Scalable Architecture – Designed for multi-user cloud workloads

System Architecture:

<img width="229" height="443" alt="image" src="https://github.com/user-attachments/assets/2e7edf1e-5816-49dc-a80d-ec08e743ce13" />

📦 Tech Stack

Backend: Node.js, Express
Database: PostgreSQL
Storage: AWS S3
Auth: JSON Web Tokens (JWT)
Deployment: Docker, Docker Compose
Other: Bcrypt, Multer, AWS SDK v3

🛠️ Installation & Setup
1️⃣ Clone the repository
git clone https://github.com/YOUR_USERNAME/CloudBox.git
cd CloudBox

2️⃣ Create a .env file
PORT=8000

DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=cloudbox

JWT_SECRET=your_jwt_secret_here

AWS_REGION=ap-south-1
AWS_S3_BUCKET=your_bucket_name
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

3️⃣ Start using Docker
docker-compose up --build


Backend → http://localhost:8000

Postgres → localhost:5432 (inside container)

📚 API Documentation
Auth
Method	Endpoint	Description
POST	/auth/signup	Register a new user
POST	/auth/login	Authenticate user & return a JWT
Files
Method	Endpoint	Description
POST	/files/upload	Upload a file to a folder
GET	/files/list?folder_id=	List files & subfolders
GET	/files/:id/download	Download file
DELETE	/files/:id	Delete file
PATCH	/files/:id/rename	Rename file
Folders
Method	Endpoint	Description
POST	/folders/create	Create a new folder
GET	/folders/list	List user folders
PATCH	/folders/:id/rename	Rename folder
DELETE	/folders/:id	Delete folder

All file/folder routes require Authorization: Bearer <JWT>

🧪 Project Structure
cloudbox/
│── src/
│   ├── controllers/
│   ├── services/
│   ├── routes/
│   ├── middleware/
│   ├── config/
│   └── db/
│── docker-compose.yml
│── Dockerfile
│── package.json
│── README.md

🖼️ Screenshots

(Replace with actual screenshots)

File Upload UI

Folder Explorer

API Testing via Postman

🚧 Future Improvements

🔄 File versioning

👥 Team folders & sharing

🔎 Full-text search for files

📊 Usage analytics dashboard

🛡️ Role-based access control (RBAC)

🧑‍💻 Author

Saad Faheem Khan Pattan
Vellore Institute of Technology
GitHub: https://github.com/saadfaheem07
