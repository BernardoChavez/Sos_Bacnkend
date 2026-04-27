# 🏎️ SOS Automotriz - Inteligencia Artificial & Rescate Vial (Backend)

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)

Backend robusto diseñado para la gestión de emergencias automotrices en tiempo real. Utiliza **Google Gemini 1.5 Flash** para el análisis multimodal de incidentes y **SQLAlchemy** para una persistencia de datos segura y escalable.

## 🚀 Características Principales
- **🧠 Diagnóstico IA Multimodal**: Análisis automático de audios y fotografías de incidentes para generar fichas técnicas mecánicas.
- **📍 Asignación Inteligente**: Algoritmo basado en la fórmula de Haversine para encontrar el taller más cercano y capacitado.
- **⏱️ Auditoría Forense**: Sistema de trazabilidad detallado que registra cada acción, monto y cambio de estado.
- **🔔 Notificaciones Duales**: Integración de WebSockets para alertas en tiempo real y notificaciones persistentes en base de datos.
- **💳 Gestión Financiera**: Control de liquidaciones, comisiones por servicio y soporte para múltiples métodos de pago.

## 🛠️ Stack Tecnológico
- **Core**: FastAPI (Python 3.10+)
- **Base de Datos**: PostgreSQL / Supabase
- **ORM**: SQLAlchemy
- **IA**: Google Generative AI (Gemini SDK)
- **Seguridad**: JWT (JSON Web Tokens) & Passlib (Bcrypt)

## 🔧 Instalación y Despliegue
1. Clonar el repositorio.
2. Crear un entorno virtual: `python -m venv venv`.
3. Instalar dependencias: `pip install -r requirements.txt`.
4. Configurar el archivo `.env` (basado en `.env.example`).
5. Iniciar servidor: `uvicorn app.main:app --reload`.

---
Desarrollado por **Bernardo Chavez**
