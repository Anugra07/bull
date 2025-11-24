# Bull - Carbon Offset Land Analyzer

## Quick Start

### Running the Application

Simply run the startup script:

```bash
./start.sh
```

This will start both the backend and frontend servers automatically.

**URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

**To stop both servers:** Press `Ctrl+C` in the terminal

---

## Manual Setup (if needed)

### Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Create a `.env` file in the `backend` directory with:

```env
# Google Earth Engine
GEE_SERVICE_ACCOUNT=your-service-account@your-project.iam.gserviceaccount.com
GEE_PRIVATE_KEY={"type":"service_account",...}

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

Create a `.env.local` file in the `frontend` directory with:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

## Features

- ✅ **Environmental Metrics**: NDVI, EVI, Biomass, Canopy Height, SOC, Rainfall
- ✅ **Time-Series Trends**: 5-year NDVI trends, fire detection, rainfall anomalies
- ✅ **Carbon Offset Potential**: Ecosystem-specific sequestration calculations
- ✅ **MRV Baseline**: Baseline vs. Project carbon stock with additionality (carbon credits)
- ✅ **Risk Assessment**: Fire risk, drought risk, trend loss adjustments

---

## Technology Stack

**Frontend:**
- Next.js
- React
- Tailwind CSS
- TypeScript

**Backend:**
- FastAPI (Python)
- Google Earth Engine
- Supabase
- GeoPandas, Shapely, Rasterio

---

## Documentation

See `PARAMETERS_DOCUMENTATION.md` for detailed information about:
- Data sources
- Carbon calculation methodology
- Time-series analysis
- MRV baseline scenarios
