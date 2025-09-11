# 🎨 Architecture Diagram Preview

## What the Mermaid Diagram Shows

The architecture diagram in both `README.md` and `docs/architecture-diagram.md` will render as a visual flowchart showing:

### **👤 User Layer (Top)**
- Desktop User (connects to PyQt6 app)
- Web User (connects to Next.js dashboard)

### **💻 Client Layer** 
- **Desktop App Section**: Shows PyQt6 app with Eye Tracker, Local Storage
- **Web Dashboard Section**: Shows Next.js with real-time analytics

### **⚡ Backend Layer**
- FastAPI Server with REST API and JWT Authentication
- Data Sync Engine for offline-first functionality

### **🗄️ Data Layer**
- Database (SQLite → PostgreSQL transition)
- Cloud Database (AWS RDS PostgreSQL)

### **🏗️ Infrastructure Layer**
- Render.com for production hosting
- GitHub Actions for CI/CD

## Visual Flow
The diagram shows data flow arrows connecting:
1. Users to their respective applications
2. Applications to backend via HTTPS/JWT
3. Backend to database and sync engine
4. Infrastructure deployment connections

## Color Coding
- **Blue**: User interactions
- **Purple**: Client applications  
- **Green**: Backend services
- **Orange**: Data storage
- **Red**: Infrastructure & deployment

This provides a clear visual overview of how all components interact in the Wellness at Work system!

---

## Viewing the Diagrams

### In GitHub/GitLab
The Mermaid diagrams will render automatically when viewing the markdown files on GitHub, GitLab, or other platforms that support Mermaid.

### In Local Markdown Viewers
- **VS Code**: Install "Markdown Preview Mermaid Support" extension
- **Typora**: Built-in Mermaid support
- **GitKraken Glo Boards**: Native support
- **Online**: Copy the mermaid code to https://mermaid.live/

### In Documentation Sites
- **GitBook**: Native Mermaid support
- **Notion**: Native Mermaid support  
- **Confluence**: Via Mermaid macro
- **Wiki.js**: Built-in support
