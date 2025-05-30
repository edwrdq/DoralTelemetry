#!/usr/bin/env python3
"""
Laptop-Side Bridge: COM-Port -> JSON -> Websocket + CSV
Run: python pc_bridge.py, then open http://localhost:8000
"""

import json, threading, asyncio, time, io
from collections import deque
import serial
from fastapi import FastAPI, WebSocket, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
import uvicorn

#----- Serial Settings -----
COM = "COM9" # Check device manager, incoming SPP port
BAUD = 512_000
UART = serial.Serial(COM, BAUD, timeout=0.02)

