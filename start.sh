#!/bin/bash

# Startup script for Bull - Carbon Offset Land Analyzer
# This script starts both backend and frontend servers

echo "🚀 Starting Bull - Carbon Offset Land Analyzer..."
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Start backend in background
echo "📡 Starting backend server..."
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend running on http://localhost:8000 (PID: $BACKEND_PID)"

# Wait a moment for backend to start
sleep 2

# Start frontend in background
echo ""
echo "🎨 Starting frontend server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend running on http://localhost:3000 (PID: $FRONTEND_PID)"

echo ""
echo "✅ Both servers started successfully!"
echo ""
echo "📝 URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for Ctrl+C
trap "echo ''; echo '⏹️  Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Servers stopped.'; exit 0" INT

# Keep script running
wait
