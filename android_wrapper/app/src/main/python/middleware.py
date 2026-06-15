"""
VTHC Middleware - RFID Bridge Application
Single file version with all functionality consolidated
Compatible with Flask on Termux and desktop
"""

import xmlrpc.client
import logging
import traceback
import os
import time
import json
from io import BytesIO
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, Response

app = Flask(__name__)
app.secret_key = "VEHRAD_ODOO_ENTERPRISE_THEME_RFID_2026"

# Setup basic logging to file and console for debugging Odoo exceptions
APP_BASE_DIR = os.path.expanduser("~")
LOG_PATH = os.path.join(APP_BASE_DIR, 'vthc_error.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Global in-memory structural cache layer to keep middleware processing lightning fast
GLOBAL_PERFORMANCE_CACHE = {
    'locations': None,
    'locations_expiry': 0,
    'partners': None,
    'partners_expiry': 0,
    'documents': {},
    'documents_expiry': {},
    'available_stock': {},
    'available_stock_expiry': {}
}
CACHE_TTL = 300  # 5 Minutes cache validity window before silent re-fetching
DOC_CACHE_TTL = 20
STOCK_CACHE_TTL = 15


def _cache_key(db_name, mode=None, product_id=None):
    if product_id is not None:
        return f"{db_name}:{product_id}"
    if mode is not None:
        return f"{db_name}:{mode}"
    return db_name


def invalidate_runtime_cache():
    """Drop fast-changing cache buckets after user write operations."""
    GLOBAL_PERFORMANCE_CACHE['documents'].clear()
    GLOBAL_PERFORMANCE_CACHE['documents_expiry'].clear()
    GLOBAL_PERFORMANCE_CACHE['available_stock'].clear()
    GLOBAL_PERFORMANCE_CACHE['available_stock_expiry'].clear()


# =====================================================================
# HTML TEMPLATE - Modern Odoo Design
# =====================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no">
    <meta name="theme-color" content="#714b67">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="VTHC Middleware">
    <link rel="manifest" href="/manifest.webmanifest">
    <title>Odoo Inventory Operations - VTHC Middleware</title>
    <style>
        :root {
            color-scheme: light;
            --bg: #f5f6fa;
            --surface: #ffffff;
            --surface-alt: #f6f7fb;
            --border: #dfe3ee;
            --text: #253249;
            --muted: #718096;
            --primary: #714b67;
            --primary-dark: #5a3c52;
            --accent: #00a09d;
            --danger: #e04f5f;
            --success: #00a09d;
            --shadow: 0 10px 25px rgba(44, 62, 80, 0.08);
            --shadow-soft: 0 2px 8px rgba(44, 62, 80, 0.08);
        }

        * {
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            max-width: 100%;
            overflow-x: hidden;
            min-height: 100%;
            font-family: "Segoe UI Variable", "Segoe UI", Tahoma, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
        }

        body {
            line-height: 1.3;
            background-image: radial-gradient(circle at 10% -10%, rgba(113, 75, 103, 0.08) 0%, rgba(113, 75, 103, 0) 42%), radial-gradient(circle at 100% 0%, rgba(0, 160, 157, 0.08) 0%, rgba(0, 160, 157, 0) 36%);
            background-attachment: fixed;
        }

        .app-shell {
            width: 100%;
            max-width: 100%;
            overflow: visible;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .container {
            width: 100%;
            max-width: 100%;
            padding: 0.4rem 0.3rem;
        }

        .topbar {
            background: linear-gradient(100deg, var(--primary) 0%, #7b536f 55%, #5d4055 100%);
            box-shadow: 0 10px 24px rgba(90, 60, 82, 0.26);
            position: sticky;
            top: 0;
            z-index: 20;
            width: 100%;
            border-bottom: 1px solid rgba(255, 255, 255, 0.18);
        }

        .topbar-inner {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.25rem;
            padding: 0.5rem 0.4rem;
            width: 100%;
        }

        .brand-group {
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .brand-link {
            font-size: 1.15rem;
            font-weight: 700;
            color: #fff;
            text-decoration: none;
            letter-spacing: -0.02em;
        }

        .brand-meta {
            font-size: 0.8rem;
            color: rgba(255, 255, 255, 0.85);
            font-weight: 400;
            border-left: 1px solid rgba(255, 255, 255, 0.3);
            padding-left: 0.3rem;
            margin-left: 0.1rem;
        }

        .topbar-actions {
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .topbar-user {
            font-size: 0.75rem;
            color: #fff;
            font-weight: 500;
            max-width: 90px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .btn {
            border: 1px solid transparent;
            cursor: pointer;
            border-radius: 6px;
            padding: 0.6rem 0.8rem;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 150ms ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 40px;
        }

        .btn-sm {
            padding: 0.25rem 0.4rem;
            font-size: 0.7rem;
            min-height: auto;
            height: 28px;
        }

        .btn-light {
            background: rgba(255, 255, 255, 0.15);
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.25);
        }

        .btn-light:hover {
            background: rgba(255, 255, 255, 0.25);
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary) 0%, #835b78 100%);
            color: #fff;
            box-shadow: var(--shadow-soft);
        }

        .btn-primary:hover {
            background-color: var(--primary-dark);
        }

        .btn-accent {
            background-color: var(--accent);
            color: #fff;
        }

        .btn-accent:hover {
            background-color: #008683;
        }
        
        .btn-accent { display: none; }

        .btn-secondary {
            background: var(--surface-alt);
            color: var(--text);
            border: 1px solid #d1d5db;
            box-shadow: var(--shadow-soft);
        }

        .btn-secondary:hover {
            background: #e5e7eb;
        }

        .btn-block {
            width: 100%;
        }

        .btn:disabled,
        .btn.btn-loading {
            opacity: 0.6;
            cursor: not-allowed;
            pointer-events: none;
        }

        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top: 2px solid #fff;
            border-radius: 50%;
            animation: spin-loader 0.8s linear infinite;
            margin-right: 6px;
        }

        @keyframes spin-loader {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            box-shadow: var(--shadow);
            padding: 0.8rem 0.65rem;
            margin-top: 0.45rem;
            width: 100%;
        }

        .summary-panel {
            border-top: 3px solid rgba(113, 75, 103, 0.38);
        }

        .line-sheet-head {
            margin: 0.25rem 0 0.55rem;
            font-size: 1rem;
            color: #2d3a52;
            font-weight: 700;
        }

        .line-sheet-note {
            margin: 0 0 0.6rem;
            color: var(--muted);
            font-size: 0.78rem;
        }

        .line-pager {
            border: 1px solid #d2dae8;
            border-radius: 6px;
            background: #f8fafe;
            padding: 0.45rem;
            margin: 0 0 0.55rem;
        }

        .line-pager-row {
            display: flex;
            align-items: center;
            gap: 0.35rem;
            width: 100%;
        }

        .line-pager-row + .line-pager-row {
            margin-top: 0.35rem;
        }

        .line-pager-status {
            flex: 1;
            text-align: center;
            font-size: 0.76rem;
            font-weight: 700;
            color: #344a6c;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .line-pager-select {
            width: 100%;
            border: 1px solid #c8d2e5;
            border-radius: 4px;
            background: #fff;
            color: #30445f;
            padding: 0.35rem 0.45rem;
            font-size: 0.78rem;
            min-height: 32px;
        }

        .line-page-hidden {
            display: none !important;
        }

        .batch-settings-card {
            background: #f9fbff;
            border: 1px solid #cdd8eb;
            border-radius: 6px;
            padding: 0.75rem;
            margin: 0.15rem 0 0.35rem;
        }

        .section-caption {
            margin: 0 0 0.45rem;
            font-size: 0.8rem;
            font-weight: 700;
            color: #33415c;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .panel-header h1 {
            margin: 0;
            font-size: 1.15rem;
            color: var(--primary);
            font-weight: 600;
        }

        .panel-subtitle {
            margin: 0.25rem 0 0.75rem;
            color: var(--muted);
            font-size: 0.8rem;
        }

        .form-grid {
            display: grid;
            gap: 0.6rem;
            width: 100%;
        }

        .form-label {
            display: grid;
            gap: 0.25rem;
            font-size: 0.78rem;
            font-weight: 600;
            color: #3f4f69;
            width: 100%;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        .form-label input,
        .form-label select {
            width: 100%;
            max-width: 100%;
            border-radius: 3px;
            border: 1px solid #c5cedf;
            background: #fff;
            color: var(--text);
            padding: 0.5rem;
            font-size: 0.86rem;
            font-weight: 400;
            height: 40px;
            text-transform: none;
            letter-spacing: normal;
        }

        .form-label input:focus,
        .form-label select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(113, 75, 103, 0.1);
        }

        .alert-box {
            border-radius: 4px;
            padding: 0.6rem;
            margin-bottom: 0.3rem;
            font-weight: 500;
            font-size: 0.8rem;
            word-break: break-word;
        }

        .alert-success {
            background: #e6f6f6;
            border: 1px solid #bce3e3;
            color: #007371;
        }

        .alert-danger {
            background: #fde8e8;
            border: 1px solid #f8b4b4;
            color: #9b1c1c;
        }

        .status-row {
            display: flex;
            gap: 0.4rem;
            margin-bottom: 0.75rem;
            width: 100%;
        }

        .status-item {
            background: var(--surface-alt);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.3rem 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.3rem;
            width: 100%;
        }

        .status-label {
            font-size: 0.7rem;
            font-weight: 700;
            color: var(--muted);
            text-transform: uppercase;
        }

        .status-value {
            font-size: 0.8rem;
            color: var(--text);
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .mode-tabs {
            display: flex;
            border: 1px solid #d5dceb;
            border-radius: 7px;
            background: #f8fafe;
            margin-bottom: 0.75rem;
            gap: 0;
            width: 100%;
            overflow: hidden;
        }

        .mode-tab {
            flex: 1;
            padding: 0.48rem 0.22rem;
            text-align: center;
            color: #4d5f7e;
            text-decoration: none;
            font-size: 0.82rem;
            font-weight: 600;
            border-right: 1px solid #d5dceb;
        }

        .mode-tab:last-child {
            border-right: none;
        }

        .mode-tab:hover {
            color: var(--primary);
        }

        .mode-tab.active {
            color: #fff;
            background: #6f4f67;
        }

        .tracking-panel {
            background: #fff;
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.5rem;
            margin-top: 0.1rem;
            width: 100%;
            max-width: 100%;
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.6rem;
            width: 100%;
        }
        
        @media (min-width: 600px) {
            .form-row-three {
                grid-template-columns: 1fr 1fr 1fr;
            }
        }

        .scanner-panel {
            margin-top: 0.55rem;
            border: 1px solid #d6deeb;
            border-radius: 6px;
            background: #fbfcff;
            padding: 0.5rem;
            width: 100%;
        }

        .scanner-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
            gap: 0.4rem;
            width: 100%;
        }

        .scanner-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--primary);
        }

        .scanner-note {
            color: var(--muted);
            font-size: 0.7rem;
        }

        .scanner-status {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 0.25rem 0.5rem;
            background: #fff;
            font-size: 0.7rem;
            font-weight: 600;
        }

        .status-dot {
            width: 0.45rem;
            height: 0.45rem;
            background: var(--danger);
            border-radius: 50%;
        }

        .status-dot.dot-green {
            background: #10b981;
            animation: pulse-glow 1.5s infinite;
        }

        @keyframes pulse-glow {
            0% { opacity: 0.5; }
            50% { opacity: 1; }
            100% { opacity: 0.5; }
        }

        .scanner-input {
            width: 1px;
            height: 1px;
            opacity: 0;
            border: none;
            margin: 0;
            padding: 0;
            position: absolute;
            top: 0;
            left: 0;
            z-index: -1;
        }

        .registry-card {
            margin-top: 0.5rem;
            border: 1px solid #d4dcea;
            border-radius: 3px;
            overflow: hidden;
            width: 100%;
            max-width: 100%;
        }

        .registry-head {
            display: grid;
            grid-template-columns: 30px minmax(0, 1fr) 55px;
            padding: 0.4rem;
            color: #5a6b86;
            font-size: 0.7rem;
            text-transform: uppercase;
            font-weight: 700;
            background: #f3f6fc;
            border-bottom: 1px solid #d8e0ee;
            width: 100%;
        }

        .registry-body {
            display: grid;
            max-height: 160px;
            overflow-y: auto;
            overflow-x: hidden;
            background: #fff;
            width: 100%;
        }

        .registry-row {
            display: grid;
            grid-template-columns: 30px minmax(0, 1fr) 55px;
            align-items: center;
            padding: 0.3rem 0.4rem;
            border-bottom: 1px solid var(--border);
            width: 100%;
        }

        .registry-row:last-child {
            border-bottom: none;
        }

        .registry-row .tag-string {
            color: var(--text);
            font-family: monospace;
            font-size: 0.8rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding-right: 0.2rem;
        }

        .empty-state {
            color: var(--muted);
            padding: 1rem 0.25rem;
            text-align: center;
            font-size: 0.75rem;
        }

        .btn-row-remove {
            background: transparent;
            color: var(--danger);
            border: 1px solid #fca5a5;
            border-radius: 4px;
            padding: 0.15rem 0.3rem;
            font-size: 0.7rem;
            height: 24px;
            min-height: auto;
            cursor: pointer;
            width: 100%;
            text-align: center;
        }

        .btn-row-remove:hover {
            background: var(--danger);
            color: white;
        }

        .registry-footer {
            margin-top: 0.4rem;
            text-align: right;
            color: var(--muted);
            font-size: 0.75rem;
            font-weight: 600;
        }

        .scan-collapsible {
            margin-top: 0.35rem;
            background: transparent;
            overflow: visible;
        }

        .scan-toggle-btn {
            width: auto;
            border: 1px solid #cfd9ea;
            border-radius: 999px;
            background: #f5f8ff;
            color: #385072;
            font-size: 0.68rem;
            font-weight: 700;
            line-height: 1;
            text-align: left;
            padding: 0.28rem 0.5rem;
            cursor: pointer;
            min-height: 24px;
            display: inline-flex;
            align-items: center;
            white-space: nowrap;
        }
        /* Custom Popup Styles */
.custom-alert-overlay {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center; justify-content: center;
    z-index: 10000;
}

.custom-alert-box {
    background: white;
    padding: 24px;
    border-radius: 12px;
    max-width: 85%;
    width: 320px;
    text-align: center;
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    font-family: sans-serif;
}

.custom-alert-msg {
    color: #444;
    font-size: 15px;
    margin-bottom: 22px;
    line-height: 1.5;
}

.custom-alert-btn {
    background: #6c4a71; /* Matches your purple theme */
    color: white;
    border: none;
    padding: 10px 32px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}

.custom-alert-btn:hover {
    background: #5a3d5e;
}

        .scan-toggle-btn:hover {
            background: #edf3ff;
            border-color: #bccae2;
        }

        .scan-collapsible-body {
            display: none;
            padding: 0.35rem 0 0;
            background: #fff;
        }

        .scan-collapsible.open .scan-collapsible-body {
            display: block;
        }

        .scan-collapsible .registry-card {
            margin-top: 0;
        }

        .btn-validate {
            margin-top: 0.55rem;
            padding: 0.6rem;
            font-size: 0.9rem;
        }

        .hidden {
            display: none !important;
        }

        .variant-box {
            border: 1px solid #ced7e5;
            border-radius: 6px;
            padding: 0.65rem;
            margin-bottom: 0.7rem;
            background: #ffffff;
            box-shadow: 0 1px 2px rgba(55, 75, 105, 0.08);
        }
        
        .variant-title-banner {
            background: #f4f7fd;
            color: #263956;
            border: 1px solid #d7dfed;
            padding: 0.4rem 0.5rem;
            margin: -0.65rem -0.65rem 0.55rem -0.65rem;
            border-radius: 6px 6px 0 0;
            font-weight: 700;
            font-size: 0.84rem;
            letter-spacing: 0.02em;
        }
        
        .remove-btn{
            color: var(--danger);
            border: none;
        }

        .inline-select-search {
            width: 100%;
            border-radius: 6px;
            border: 1px solid #ccd3e2;
            background: #ffffff;
            color: var(--text);
            padding: 0.45rem 0.5rem;
            font-size: 0.84rem;
            margin-bottom: 0.35rem;
        }

        .inline-select-search:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(113, 75, 103, 0.12);
        }

        /* Custom Select Component - Modern Odoo Style */
        .custom-select-wrapper {
            position: relative;
            width: 100%;
        }

        .custom-select-container {
            position: relative;
            width: 100%;
        }

        .custom-select-container.dropdown-open {
            z-index: 5000;
        }

        .custom-select-input {
            width: 100%;
            border-radius: 6px;
            border: 1.5px solid #d0d0d0;
            background: #fff;
            color: var(--text);
            padding: 0.6rem 0.5rem 0.6rem 0.5rem;
            font-size: 0.95rem;
            font-weight: 400;
            height: 42px;
            cursor: pointer;
            padding-right: 35px;
            transition: all 0.15s ease;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            text-align: left;
            display: flex;
            align-items: center;
        }

        button.custom-select-input {
            appearance: none;
            -webkit-appearance: none;
        }

        .custom-select-input:hover {
            border-color: var(--primary);
            box-shadow: 0 2px 4px rgba(113, 75, 103, 0.08);
        }

        .custom-select-input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(113, 75, 103, 0.1);
            background: #fafafa;
        }

        .custom-select-input::placeholder {
            color: #a0a0a0;
        }

        .custom-select-input.is-placeholder {
            color: #a0a0a0;
        }

        .custom-select-arrow {
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            pointer-events: none;
            color: var(--primary);
            font-size: 0.6rem;
            font-weight: bold;
            transition: transform 0.2s ease;
        }

        .custom-select-options.open .custom-select-arrow {
            transform: translateY(-50%) rotate(180deg);
        }

        .custom-select-hidden {
            display: none !important;
        }

        .custom-select-options {
            position: fixed;
            top: 0;
            left: 0;
            right: auto;
            background: #fff;
            border: 1.5px solid #d0d0d0;
            border-radius: 6px;
            display: none;
            max-height: 0;
            overflow: hidden;
            z-index: 99999;
            transition: max-height 0.25s ease, box-shadow 0.25s ease;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        .custom-select-options.open {
            display: block;
            max-height: 320px;
            overflow-y: auto;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
        }

        .custom-select-search {
            display: none;
            width: 100%;
            border: none;
            border-bottom: 1.5px solid #e5e5e5;
            padding: 0.6rem 0.5rem;
            font-size: 0.95rem;
            box-sizing: border-box;
            background: #f8f8f8;
            color: var(--text);
        }

        .custom-select-search-toggle {
            width: 100%;
            border: none;
            border-bottom: 1.5px solid #e5e5e5;
            background: #f8f8f8;
            color: var(--primary);
            text-align: left;
            padding: 0.55rem 0.5rem;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
        }

        .custom-select-options.search-active .custom-select-search-toggle {
            display: none;
        }

        .custom-select-options.search-active .custom-select-search {
            display: block;
        }

        .custom-select-search:focus {
            outline: none;
            background: #f3f3f3;
            border-bottom-color: var(--primary);
        }

        .custom-select-search::placeholder {
            color: #a0a0a0;
        }

        .options-list {
            max-height: 270px;
            overflow-y: auto;
            overflow-x: hidden;
        }

        .options-list::-webkit-scrollbar {
            width: 6px;
        }

        .options-list::-webkit-scrollbar-track {
            background: #f1f1f1;
        }

        .options-list::-webkit-scrollbar-thumb {
            background: #ccc;
            border-radius: 3px;
        }

        .options-list::-webkit-scrollbar-thumb:hover {
            background: #999;
        }

        .option-item {
            padding: 0.7rem 0.6rem;
            cursor: pointer;
            border-bottom: 1px solid #f3f3f3;
            transition: background-color 0.1s ease;
            min-width: 0;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .option-item:last-child {
            border-bottom: none;
        }

        .option-item:hover {
            background-color: #f9f9f9;
            border-left: 3px solid var(--primary);
            padding-left: calc(0.6rem - 3px);
        }

        .option-item.selected {
            background-color: #f1f2f6;
            border-left: 3px solid var(--primary);
            padding-left: calc(0.6rem - 3px);
        }

        .option-title {
            font-weight: 500;
            color: var(--text);
            font-size: 0.95rem;
            line-height: 1.3;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .option-subtitle {
            font-size: 0.8rem;
            color: var(--muted);
            margin-top: 0.15rem;
            line-height: 1.2;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .option-empty {
            padding: 1rem;
            text-align: center;
            color: var(--muted);
            font-size: 0.9rem;
        }
/* --- Multi-Lot Split Layout Allocations Styles (FIXED & UPDATED) --- */

/* 1. Main Container: Centers the entire table area */
.lot-pool-box {
    width: 100% !important;
    max-width: 700px !important;
    margin: 15px auto !important;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

/* 2. The Table: Enables horizontal scroll on mobile instead of squishing */
.allocation-table {
    width: 100% !important;
    display: block !important;
    overflow-x: auto !important; 
    border: none !important;
    background: #fff !important;
    border-radius: 4px;
    box-shadow: var(--shadow-soft);
}

/* 3. The Grid: Forces Header and Rows to align perfectly in 3 columns */
.allocation-header, 
.allocation-row, 
.allocation-row-card, 
#allocation_container_8 > div {
    display: grid !important;
    grid-template-columns: 1fr 85px 85px !important; /* BL | QTY | ACTION */
    width: 100% !important;
    min-width: 380px !important; /* Safety for mobile */
    align-items: center !important;
    border: none !important;
    border-bottom: 1px solid #f0f2f5 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* 4. Professional Header Styling */
.allocation-header {
    background: #f8f9fa !important;
    border-bottom: 2px solid #dee2e6 !important;
    color: var(--muted) !important;
    font-weight: 700 !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    height: 38px !important;
    display: grid !important;
}

/* 5. Column Cell Spacing and Text */
.allocation-header span, 
.lot-label, 
.qty-row, 
.delete-row {
    padding: 0 12px !important;
    display: flex !important;
    align-items: center !important;
    height: 40px !important;
}

.lot-label {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--text) !important;
    white-space: nowrap; 
    overflow: hidden; 
    text-overflow: ellipsis;
}

/* 6. Centering Content for Qty and Action columns */
.qty-row, .delete-row, 
.allocation-header span:nth-child(2), 
.allocation-header span:nth-child(3) {
    justify-content: center !important;
}

/* 7. Borderless Quantity Input (Clean Odoo Style) */
.allocation-input {
    all: unset !important;
    width: 100% !important;
    height: 100% !important;
    text-align: center !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: var(--text) !important;
}

/* 8. Red Text-Only Remove Action */
.btn-row-remove {
    all: unset !important;
    color: var(--danger) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    text-align: center !important;
    width: 100% !important;
}

.btn-row-remove:hover {
    text-decoration: underline !important;
}

/* 9. Cleanup: Hide internal row labels if they appear */
.qty-row div, .qty-row p, .qty-row span:not(.allocation-input) {
    display: none !important;
}
        .allocation-toolbar {
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.25rem;
            margin-top: 0.25rem;
            margin-bottom: 0.4rem;
            align-items: stretch;
            width: 100%;
            min-width: 0;
        }

        .allocation-select {
            flex: 1;
            min-width: 0;
            height: 34px;
            font-size: 0.85rem;
            width: 100%;
            max-width: 100%;
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        select.js-searchable-select:not(.custom-select-hidden) {
            width: 100%;
            max-width: 100%;
            min-width: 0;
            display: block;
        }

        .allocation-add-btn {
            flex: 0 0 auto;
            white-space: nowrap;
            min-width: 58px;
            width: 100%;
            margin-bottom: 0.35rem;
        }

        .allocation-toolbar .custom-select-wrapper,
        .allocation-toolbar .custom-select-container,
        .allocation-toolbar .custom-select-input,
        .allocation-toolbar .custom-select-options {
            width: 100%;
            min-width: 0;
        }

        .variant-box,
        .lot-pool-box,
        .summary-panel,
        .card {
            max-width: 100%;
            min-width: 0;
        }

        .scanner-panel,
        .registry-card,
        .allocation-table {
            max-width: 100%;
            min-width: 0;
            overflow-x: hidden;
        }

        .select-panel,
        .form-grid,
        .custom-select-wrapper,
        .custom-select-container {
            overflow: visible;
        }

        .registry-head,
        .registry-row {
            min-width: 0;
        }

        .registry-head span,
        .registry-row span,
        .scanner-note,
        .scanner-title,
        .status-text {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .scanner-status {
            max-width: 100%;
        }

        @media (max-width: 768px) {
            .allocation-add-btn {
                width: 100%;
            }

            .registry-head,
            .registry-row {
                grid-template-columns: 26px minmax(0, 1fr) 54px;
            }

            .scanner-header {
                flex-direction: column;
                align-items: flex-start;
            }

            .scanner-status {
                align-self: flex-start;
                margin-top: 0.2rem;
            }
        }

        .lot-scan-summary {
            border: 1px solid var(--border);
            border-radius: 4px;
            background: #fff;
            margin-top: 0;
            overflow: hidden;
        }

        .lot-scan-summary-row {
            padding: 0.35rem 0.5rem;
            border-bottom: 1px solid var(--border);
            display: grid;
            gap: 0.15rem;
        }

        .lot-scan-summary-row:last-child {
            border-bottom: none;
        }

        .lot-scan-summary-head {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text);
            font-weight: 600;
        }

        .lot-scan-summary-tags {
            font-family: monospace;
            font-size: 0.72rem;
            color: var(--muted);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
@media (max-width: 500px) {
    /* 1. Reset width and min-width for all containers */
    html,
    body,
    .app-shell,
    .content,
    .container,
    .summary-panel,
    .variant-box,
    .lot-pool-box,
    .scanner-panel,
    .registry-card,
    .allocation-table,
    .allocation-toolbar,
    .allocation-select,
    .allocation-add-btn,
    .custom-select-wrapper,
    .custom-select-container,
    .custom-select-input {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
    }

    body {
        overflow-x: hidden !important;
    }

    .app-shell,
    .container,
    .content {
        overflow: visible !important;
    }

    .allocation-toolbar {
        display: grid !important;
        grid-template-columns: 1fr !important;
        gap: 0.35rem;
    }

    /* FIX: High-specificity grid. Using [id^=...] to work with any line container ID */
    div.lot-pool-box .allocation-table .allocation-header,
    [id^="allocation_container_"] div.allocation-row-card {
        display: grid !important;
        grid-template-columns: 1fr 60px 80px !important; 
        padding: 0 !important;
        margin: 0 !important;
        min-width: 0 !important;
        width: 100% !important;
        align-items: center !important;
        box-sizing: border-box !important;
    }

    /* FIX: Uniform cell behavior */
    .allocation-header > *,
    .allocation-row-card > * {
        display: flex !important;
        align-items: center !important;
        padding: 0.35rem 0.5rem !important; 
        min-width: 0 !important;
        box-sizing: border-box !important;
    }

    /* FIX: Left-align the first column (Labels) */
    .allocation-header > *:nth-child(1),
    .allocation-row-card > *:nth-child(1) {
        justify-content: flex-start !important;
        text-align: left !important;
        padding-left: 12px !important;
    }

    /* FIX: Center/Align numeric and action columns */
    .allocation-header > *:nth-child(2),
    .allocation-row-card > .qty-row {
        justify-content: center !important;
        text-align: center !important;
    }
    
    .allocation-header > *:nth-child(3),
    .allocation-row-card > .delete-row {
        justify-content: center !important; /* Action is now centered */
        text-align: center !important;
    }

    .allocation-header span,
    .allocation-row span,
    .allocation-row-card div,
    .variant-title-banner,
    .scanner-title,
    .scanner-note {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .topbar-actions,
    .brand-group {
        min-width: 0;
    }

    .topbar-user {
        max-width: 72px;
    }

    .container {
        padding: 0.35rem 0.25rem;
    }

    .card {
        padding: 0.65rem 0.45rem;
        border-radius: 8px;
    }

    .variant-box {
        padding: 0.55rem;
        margin-bottom: 0.9rem;
    }

    .variant-title-banner {
        margin: 0 0 0.55rem 0;
        border-radius: 6px;
        font-size: 0.8rem;
    }

    .mode-tab {
        font-size: 0.78rem;
        padding: 0.35rem 0.1rem;
    }

    .allocation-select {
        width: 100%;
        height: 36px;
        font-size: 0.82rem;
    }

    .allocation-add-btn {
        width: 100%;
        height: 34px;
        font-size: 0.72rem;
    }

    .lot-pool-box {
        padding: 0.45rem;
    }

    .allocation-header,
    .allocation-row-card {
        font-size: 0.7rem;
    }

    .qty-row input {
        width: 100% !important;
        max-width: 45px !important;
        text-align: center !important;
        font-size: 0.75rem !important;
    }

    .registry-head,
    .registry-row {
        grid-template-columns: 24px minmax(0, 1fr) 48px;
    }

    .btn {
        min-height: 38px;
        font-size: 0.82rem;
        padding: 0.5rem 0.55rem;
    }
}
}
       
    </style>
</head>
<body>
    <div class="app-shell">
        <header class="topbar">
            <div class="topbar-inner">
                <div class="brand-group">
                    <a href="/" class="brand-link">odoo</a>
                    <span class="brand-meta">VTHC Middleware</span>
                </div>
                {% if session.get('user_email') %}
                <div class="topbar-actions">
                    <span class="topbar-user">{{ session['user_email'] }}</span>
                    <a href="/logout" class="btn btn-sm btn-light">Exit</a>
                </div>
                {% endif %}
            </div>
        </header>
        <main class="content container">
            {% if message %}
            <div class="alert-box {{ 'alert-success' if msg_type == 'success' else 'alert-danger' }}">
                {{ message }}
            </div>
            {% endif %}
            {% if not session.get('user_email') %}
            <section class="card auth-panel">
                <div class="panel-header">
                    <h1>Database Connection</h1>
                    <p class="panel-subtitle">Log in using Odoo Web Services parameters.</p>
                </div>
                <form action="/login" method="POST" class="form-grid">
                    <label class="form-label">
                        Server URL
                        <input type="url" name="odoo_url" placeholder="https://your-odoo-domain.com" required>
                    </label>
                    <label class="form-label">
                        Database Name
                        <input type="text" name="db_name" placeholder="Enter your database name" required>
                    </label>
                    <label class="form-label">
                        Email Address
                        <input type="email" name="email" required autocomplete="off">
                    </label>
                    <label class="form-label">
                        API Key / Password
                        <input type="password" name="api_key" required placeholder="••••••••">
                    </label>
                    <button type="submit" class="btn btn-primary btn-block">Connect Instance</button>
                </form>
            </section>
            {% else %}
            <section class="card summary-panel">
                <div class="status-row">
                    <div class="status-item">
                        <span class="status-label">DB:</span>
                        <span class="status-value">{{ session['db_name'] }}</span>
                    </div>
                </div>
                <nav class="mode-tabs">
                    <a class="mode-tab {% if current_mode == 'purchase' %}active{% endif %}" href="/switch-mode/purchase">Receipts (IN)</a>
                    <a class="mode-tab {% if current_mode == 'delivery' %}active{% endif %}" href="/switch-mode/delivery">Deliveries (OUT)</a>
                </nav>
                <form action="/select-doc" method="POST" class="form-grid select-panel" id="global_doc_form">
                    <label class="form-label">
                        Source Operation Document
                        <div class="custom-select-wrapper">
                            <div class="custom-select-container">
                                <button type="button" class="custom-select-input is-placeholder" id="doc_search_display" data-placeholder="🔍 Select or search order...">🔍 Select or search order...</button>
                                <span class="custom-select-arrow">▼</span>
                                <select id="doc_select" name="doc_id" class="custom-select-hidden" onchange="updateDocumentDisplay(this); this.form.submit()">
                                    <option value="">-- Choose Order Record --</option>
                                    {% for doc in documents %}
                                    <option value="{{ doc.id }}" {% if selected_doc and selected_doc.id == doc.id %}selected{% endif %}>
                                        {{ doc.name }} {% if doc.partner_id %}({{ doc.partner_id[1] }}){% endif %}
                                    </option>
                                    {% endfor %}
                                </select>
                                <div class="custom-select-options" id="doc_options">
                                    <button type="button" class="custom-select-search-toggle">🔍 Search in list</button>
                                    <input type="text" class="custom-select-search" id="doc_search_input" placeholder="🔍 Type to search...">
                                    <div class="options-list" id="doc_options_list">
                                        {% if documents %}
                                            {% for doc in documents %}
                                            <div class="option-item" data-value="{{ doc.id }}">
                                                <div class="option-title">{{ doc.name }}</div>
                                                {% if doc.partner_id %}<div class="option-subtitle">{{ doc.partner_id[1] }}</div>{% endif %}
                                            </div>
                                            {% endfor %}
                                        {% else %}
                                            <div class="option-empty">No orders available</div>
                                        {% endif %}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </label>

                    {% if selected_doc and current_mode == 'purchase' %}
                    <div class="batch-settings-card">
                        <h4 class="section-caption">IN Header Parameters</h4>
                        <div class="form-row form-row-three">
                            <label class="form-label">
                                Lot/Serial Number (Unified)
                                <input type="text" name="global_lot_name" id="global_lot_name" placeholder="Enter batch lot sequence" autocomplete="off" required value="{{ saved_lot_name if saved_lot_name else '' }}" oninput="syncGlobalLotToInputs()">
                            </label>
                            <label class="form-label">
                                Inventory Owner
                                <select name="global_owner_id" id="global_owner_id" class="js-searchable-select" data-placeholder="Select owner..." data-search-placeholder="Search owner..." required onchange="syncGlobalOwnerToInputs()">
                                    <option value="">-- Choose Owner For All IN Items --</option>
                                    {% for partner in partners %}
                                    <option value="{{ partner.id }}" {% if selected_owner_id|int == partner.id|int or saved_owner_id|int == partner.id|int %}selected{% endif %}>{{ partner.name }}</option>
                                    {% endfor %}
                                </select>
                            </label>
                        </div>
                    </div>
                    {% endif %}
                </form>
                
                {% if selected_doc and not products %}
                <div class="alert-box alert-success" style="margin-top: 1rem;">
                    🎉 All product lines on this order sheet have been verified and validated to Odoo.
                </div>
                {% endif %}

                {% if products %}
                <div style="margin-top: 1rem;">
                    <h3 class="line-sheet-head">Order Lines Workspace</h3>
                    <p class="line-sheet-note">Process each line below, save draft per line, then run final validation once.</p>
                    <div class="line-pager hidden" id="line_pager">
                        <div class="line-pager-row">
                            <button type="button" class="btn btn-secondary btn-sm" id="line_prev_btn" onclick="goToPrevLine()">Previous</button>
                            <div class="line-pager-status" id="line_page_status">Line 1 / 1</div>
                            <button type="button" class="btn btn-secondary btn-sm" id="line_next_btn" onclick="goToNextLine()">Next</button>
                        </div>
                        <div class="line-pager-row">
                            <select id="line_page_select" class="line-pager-select" aria-label="Jump to line page">
                                {% for line_item in products %}
                                <option value="{{ loop.index0 }}">Line {{ loop.index }} - {{ line_item.product_id[1] }}</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                    
                    {% for prod in products %}
                    {% set line_key = prod.line_key %}
                    <div class="variant-box" id="variant_container_{{ line_key }}" data-line-key="{{ line_key }}" data-line-index="{{ loop.index0 }}" data-line-title="{{ prod.product_id[1] }}">
                        <div class="variant-title-banner">
                            {{ prod.product_id[1] }} | Demand: <span id="display_demand_{{ line_key }}">{{ prod.product_qty|int }}</span> units
                        </div>
                        
                        <form action="/submit-sync" method="POST" id="form_prod_{{ line_key }}" class="form-grid" onsubmit="compileTagsBeforeSubmit(event, '{{ line_key }}')">
                            <input type="hidden" name="doc_id_raw" value="{{ selected_doc.id }}">
                            <input type="hidden" name="product_id_raw" value="{{ prod.product_id[0] }}">
                            <input type="hidden" name="move_id_raw" value="{{ prod.move_id }}">
                            <input type="hidden" name="explicit_clean_qty" id="explicit_clean_qty_{{ line_key }}" value="0">
                            <input type="hidden" name="scanned_tags_csv" id="scanned_tags_csv_{{ line_key }}" value="">
                            <input type="hidden" name="global_lot_name" id="global_lot_shadow_{{ line_key }}" value="{{ saved_lot_name if saved_lot_name else '' }}">
                            <input type="hidden" name="global_owner_id" id="global_owner_shadow_{{ line_key }}" value="{{ saved_owner_id if saved_owner_id else '' }}">
                            
                            {% if current_mode == 'purchase' %}
                            <div class="form-row">
                                <label class="form-label">
                                    Destination Location
                                    <select name="location_id" id="incoming_loc_input_{{ line_key }}" class="js-searchable-select" data-placeholder="Select destination location..." data-search-placeholder="Search destination location..." required>
                                        <option value="">-- Choose Storage Location --</option>
                                        {% for loc in locations %}
                                        <option value="{{ loc.id }}" {% if saved_location_id|int == loc.id|int %}selected{% endif %}>{{ loc.complete_name }}</option>
                                        {% endfor %}
                                    </select>
                                </label>
                            </div>
                            <input type="hidden" name="lot_name" id="incoming_lot_input_{{ line_key }}">
                            <input type="hidden" name="owner_id" id="incoming_owner_input_{{ line_key }}">
                            {% else %}
                            
                            <div class="lot-pool-box">
                                <div class="allocation-toolbar">
                                    <select id="lot_pool_select_{{ line_key }}" class="js-searchable-select allocation-select" data-placeholder="Select BL option..." data-search-placeholder="Search BL..." data-product-id="{{ prod.product_id[0] }}">
                                        <option value="">-- Querying available BL... --</option>
                                    </select>
                                </div>
                                <button type="button" class="btn btn-sm btn-primary allocation-add-btn btn-block" onclick="addLotAllocationRow('{{ line_key }}')">Add BL</button>
                                
                                <div class="allocation-table">
                                    <div class="allocation-header">
                                        <span>Selected BL</span>
                                        <span>QTY</span>
                                        <span>Action</span>
                                    </div>
                                    <div id="allocation_container_{{ line_key }}">
                                        </div>
                                </div>
                                <div style="font-size: 0.75rem; text-align: right; font-weight: bold; color: var(--muted);">
                                    Total BL Qty : <span id="allocated_total_lbl_{{ line_key }}">0</span> / {{ prod.product_qty|int }}
                                </div>
                                <div class="scan-collapsible" id="lot_summary_collapse_{{ line_key }}">
                                    <button type="button" class="scan-toggle-btn" id="lot_summary_toggle_btn_{{ line_key }}" onclick="toggleLotSummary('{{ line_key }}')">BL Details (0)</button>
                                    <div class="scan-collapsible-body" id="lot_summary_collapse_body_{{ line_key }}">
                                        <div class="lot-scan-summary" id="lot_scan_summary_{{ line_key }}">
                                            <div class="empty-state" style="padding:0.5rem;">Per-lot scan list will appear here after scans.</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <input type="hidden" name="quant_selection" id="quant_selection_{{ line_key }}">
                            {% endif %}
                            
                            <div class="scanner-panel">
                                <div class="scanner-header">
                                    <div>
                                        <div class="scanner-title">RFID Scan Line</div>
                                    </div>
                                    <div class="scanner-status" id="scanner_status_indicator_{{ line_key }}">
                                        <span id="pulse_dot_{{ line_key }}" class="status-dot"></span>
                                        <span id="status_text_{{ line_key }}" class="status-text">STANDBY</span>
                                    </div>
                                </div>
                                <button type="button" id="manual_activation_btn_{{ line_key }}" class="btn btn-secondary btn-block" onclick="activateScanListeningSession('{{ line_key }}')">Initialize Scanner</button>
                                
                                <div class="scan-collapsible" id="scan_tags_collapse_{{ line_key }}">
                                    <button type="button" class="scan-toggle-btn" id="scan_tags_toggle_btn_{{ line_key }}" onclick="toggleScanTags('{{ line_key }}')">Tags (0)</button>
                                    <div class="scan-collapsible-body" id="scan_tags_collapse_body_{{ line_key }}">
                                        <div class="registry-card">
                                            <div class="registry-head">
                                                <span>#</span>
                                                <span>RFID Unique Code</span>
                                                <span>Action</span>
                                            </div>
                                            <div id="live_tag_tbody_{{ line_key }}" class="registry-body">
                                                <div class="empty-state">No barcodes registered yet. Launch monitoring window above.</div>
                                            </div>
                                        </div>
                                        <div class="registry-footer">Count: <span id="tag_counter_{{ line_key }}">0</span></div>
                                    </div>
                                </div>
                            </div>
                            
                            <button type="submit" class="btn btn-secondary btn-block btn-validate" style="border: 1px solid var(--accent); color: var(--accent);" onclick="return saveDraftLine(event, '{{ line_key }}')">Save This Line Draft</button>
                        </form>
                    </div>
                    {% endfor %}
                    
                    <div style="margin-top: 2rem; padding: 0.5rem; border-top: 2px solid var(--border);">
                        <div style="margin-bottom: 0.5rem;">
                            <button type="button" class="btn btn-secondary btn-block" onclick="location.reload()" style="height: 45px; font-weight: 600;">
                                🔄 Refresh Page
                            </button>
                        </div>
                        <form action="/validate-document-complete" method="POST" onsubmit="return confirmFinalDocumentValidation(event)">
                            <input type="hidden" name="final_doc_id" value="{{ selected_doc.id }}">
                            <button type="submit" class="btn btn-accent btn-block" style="font-size: 1.1rem; height: 50px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,160,157,0.3);">✓ Final Validate Document</button>
                        </form>
                    </div>
                </div>
                {% endif %}
            </section>
            {% endif %}
        </main>
    </div>

    <input type="text" id="live_scanner_input" class="scanner-input" autocomplete="off" disabled>

    <script>
        const accumulatedTags = {}; // Scoped accurately by product_id keys
        let isListening = false;
        let activeProductId = null;
        const linePagerState = {
            total: 0,
            activeIndex: 0
        };
        
        // Multi-lot tracker arrays to capture structural options under requirement 2
        const productLotAllocations = {};
        const productAvailableLotsPool = {};

        function positionDropdownPanel(container, optionsDiv) {
            if (!container || !optionsDiv) return;
            const rect = container.getBoundingClientRect();
            const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
            const viewportWidth = window.innerWidth || document.documentElement.clientWidth;

            let desiredHeight = Math.min(320, Math.max(140, viewportHeight - rect.bottom - 10));
            let top = rect.bottom + 2;

            if (desiredHeight < 140) {
                desiredHeight = Math.min(320, Math.max(140, rect.top - 10));
                top = Math.max(8, rect.top - desiredHeight - 2);
            }

            const width = Math.max(180, rect.width);
            const left = Math.min(Math.max(8, rect.left), Math.max(8, viewportWidth - width - 8));

            optionsDiv.style.left = `${left}px`;
            optionsDiv.style.top = `${top}px`;
            optionsDiv.style.width = `${width}px`;
            optionsDiv.style.maxHeight = `${desiredHeight}px`;
        }

        function repositionOpenDropdowns() {
            document.querySelectorAll('.custom-select-options.open').forEach((optionsDiv) => {
                const container = optionsDiv.closest('.custom-select-container');
                positionDropdownPanel(container, optionsDiv);
            });
        }

        function initializeCustomSelects() {
            function setCustomSelectDisplay(displayInput, text) {
                if (!displayInput) return;
                const placeholder = displayInput.dataset.placeholder || displayInput.getAttribute('placeholder') || 'Select option...';
                const normalized = (text || '').trim();
                const nextText = normalized || placeholder;
                if (typeof displayInput.value === 'string' && displayInput.tagName === 'INPUT') {
                    displayInput.value = nextText;
                } else {
                    displayInput.textContent = nextText;
                }
                displayInput.classList.toggle('is-placeholder', !normalized);
            }

            window.setCustomSelectDisplay = setCustomSelectDisplay;

            document.addEventListener('click', (e) => {
                const input = e.target.closest('.custom-select-input');
                const item = e.target.closest('.option-item:not(.option-empty)');
                const searchInput = e.target.closest('.custom-select-search');
                
                if (searchInput) {
                    e.stopPropagation();
                    return;
                }

                const searchToggle = e.target.closest('.custom-select-search-toggle');
                if (searchToggle) {
                    e.stopPropagation();
                    e.preventDefault();
                    const optionsDiv = searchToggle.closest('.custom-select-options');
                    const search = optionsDiv?.querySelector('.custom-select-search');
                    if (optionsDiv && search) {
                        optionsDiv.classList.add('search-active');
                        search.readOnly = false;
                        search.focus();
                    }
                    return;
                }
                
                if (item && !searchInput) {
                    e.stopPropagation();
                    e.preventDefault();
                    
                    const optionsDiv = item.closest('.custom-select-options');
                    const container = optionsDiv.closest('.custom-select-container');
                    const select = container.querySelector('select');
                    const displayInput = container.querySelector('.custom-select-input');
                    const value = item.dataset.value || '';
                    const displayText = item.querySelector('.option-title')?.textContent?.trim() || '';
                    
                    select.value = value;
                    setCustomSelectDisplay(displayInput, displayText);
                    
                    optionsDiv.classList.remove('open');
                    optionsDiv.classList.remove('search-active');
                    container.classList.remove('dropdown-open');
                    
                    const search = optionsDiv.querySelector('.custom-select-search');
                    if (search) {
                        search.readOnly = true;
                        search.value = '';
                        const optionsList = optionsDiv.querySelector('.options-list');
                        const allItems = optionsList.querySelectorAll('.option-item');
                        allItems.forEach(it => it.style.display = '');
                    }
                    
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    return;
                }
                
                if (input) {
                    e.stopPropagation();
                    e.preventDefault();
                    if (document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('custom-select-search')) {
                        document.activeElement.blur();
                    }
                    input.blur();
                    const container = input.closest('.custom-select-container');
                    const optionsDiv = container.querySelector('.custom-select-options');
                    
                    document.querySelectorAll('.custom-select-options.open').forEach((div) => {
                        if (div !== optionsDiv) {
                            div.classList.remove('open');
                            div.classList.remove('search-active');
                            div.closest('.custom-select-container')?.classList.remove('dropdown-open');
                            const search = div.querySelector('.custom-select-search');
                            if (search) {
                                search.readOnly = true;
                                search.value = '';
                            }
                        }
                    });
                    
                    optionsDiv.classList.toggle('open');
                    container.classList.toggle('dropdown-open', optionsDiv.classList.contains('open'));
                    if (optionsDiv.classList.contains('open')) {
                        positionDropdownPanel(container, optionsDiv);
                        const search = optionsDiv.querySelector('.custom-select-search');
                        if (search) {
                            search.readOnly = true;
                        }
                        optionsDiv.classList.remove('search-active');
                    }
                    
                    return;
                }
                
                closeAllCustomSelects();
            }, true);
            
            document.addEventListener('input', (e) => {
                const searchInput = e.target.closest('.custom-select-search');
                if (!searchInput) return;
                
                const optionsDiv = searchInput.closest('.custom-select-options');
                const optionsList = optionsDiv.querySelector('.options-list');
                const query = searchInput.value.toLowerCase();
                
                const items = optionsList.querySelectorAll('.option-item:not(.option-empty)');
                
                items.forEach((item) => {
                    const title = item.querySelector('.option-title')?.textContent.toLowerCase() || '';
                    const subtitle = item.querySelector('.option-subtitle')?.textContent.toLowerCase() || '';
                    const matches = title.includes(query) || subtitle.includes(query);
                    item.style.display = matches ? '' : 'none';
                });
            });
            
            document.querySelectorAll('.custom-select-container').forEach((container) => {
                const select = container.querySelector('select');
                const input = container.querySelector('.custom-select-input');
                
                if (select && select.value) {
                    const option = select.options[select.selectedIndex];
                    if (option) {
                        setCustomSelectDisplay(input, option.textContent.trim());
                    }
                } else {
                    setCustomSelectDisplay(input, '');
                }
            });
        }

        function closeAllCustomSelects() {
            document.querySelectorAll('.custom-select-options').forEach((div) => {
                div.classList.remove('open');
                div.closest('.custom-select-container')?.classList.remove('dropdown-open');
                div.classList.remove('search-active');
                div.style.left = '';
                div.style.top = '';
                div.style.width = '';
                div.style.maxHeight = '';
                const searchInput = div.querySelector('.custom-select-search');
                if (searchInput) {
                    searchInput.blur();
                    searchInput.readOnly = true;
                    searchInput.value = '';
                    const optionsList = div.querySelector('.options-list');
                    const allItems = optionsList.querySelectorAll('.option-item');
                    allItems.forEach(item => item.style.display = '');
                }
            });
        }

        function updateDocumentDisplay(select) {
            const displayEl = document.getElementById('doc_search_display');
            if (displayEl && typeof window.setCustomSelectDisplay === 'function') {
                const option = select.options[select.selectedIndex];
                window.setCustomSelectDisplay(displayEl, select.value && option ? option.textContent : '');
            }
        }

        function renderEnhancedSearchableOptions(select) {
            const host = select.closest('.custom-select-container.dynamic-searchable');
            if (!host) return;

            const displayInput = host.querySelector('.custom-select-input');
            const list = host.querySelector('.options-list');
            if (!displayInput || !list) return;

            const selectedOption = select.options[select.selectedIndex];
            if (typeof window.setCustomSelectDisplay === 'function') {
                window.setCustomSelectDisplay(displayInput, selectedOption && select.value ? selectedOption.textContent.trim() : '');
            }

            list.innerHTML = '';
            let hasOptions = false;
            for (let i = 0; i < select.options.length; i += 1) {
                const opt = select.options[i];
                if (!opt.value) {
                    continue;
                }
                hasOptions = true;
                const item = document.createElement('div');
                item.className = 'option-item';
                if (opt.value === select.value) {
                    item.classList.add('selected');
                }
                item.dataset.value = opt.value;
                const compactLabel = opt.textContent.trim();
                const fullLabel = (opt.title || '').trim();
                if (fullLabel && fullLabel !== compactLabel) {
                    item.innerHTML = `<div class="option-title">${compactLabel}</div><div class="option-subtitle">${fullLabel}</div>`;
                } else {
                    item.innerHTML = `<div class="option-title">${compactLabel}</div>`;
                }
                list.appendChild(item);
            }

            if (!hasOptions) {
                list.innerHTML = '<div class="option-empty">No options available</div>';
            }
        }

        function enhanceSearchableSelect(select) {
            if (!select || select.dataset.enhancedSearchable === '1') {
                return;
            }

            const wrapper = document.createElement('div');
            wrapper.className = 'custom-select-wrapper';
            const container = document.createElement('div');
            container.className = 'custom-select-container dynamic-searchable';

            const displayInput = document.createElement('button');
            displayInput.type = 'button';
            displayInput.className = 'custom-select-input';
            displayInput.dataset.placeholder = select.dataset.placeholder || 'Select option...';
            displayInput.textContent = displayInput.dataset.placeholder;
            displayInput.classList.add('is-placeholder');

            const arrow = document.createElement('span');
            arrow.className = 'custom-select-arrow';
            arrow.textContent = '▼';

            const optionsDiv = document.createElement('div');
            optionsDiv.className = 'custom-select-options';
            const searchInput = document.createElement('input');
            searchInput.type = 'text';
            searchInput.className = 'custom-select-search';
            searchInput.placeholder = select.dataset.searchPlaceholder || 'Search...';
            searchInput.readOnly = true;
            const searchToggle = document.createElement('button');
            searchToggle.type = 'button';
            searchToggle.className = 'custom-select-search-toggle';
            searchToggle.textContent = '🔍 Search in list';
            const list = document.createElement('div');
            list.className = 'options-list';

            optionsDiv.appendChild(searchToggle);
            optionsDiv.appendChild(searchInput);
            optionsDiv.appendChild(list);

            const parent = select.parentNode;
            parent.insertBefore(wrapper, select);
            wrapper.appendChild(container);
            container.appendChild(displayInput);
            container.appendChild(arrow);
            container.appendChild(select);
            container.appendChild(optionsDiv);

            select.classList.add('custom-select-hidden');
            select.dataset.enhancedSearchable = '1';

            renderEnhancedSearchableOptions(select);
        }

        function initializeSearchableSelects() {
            document.querySelectorAll('select.js-searchable-select').forEach((select) => {
                enhanceSearchableSelect(select);
            });
        }

        function refreshSearchableSelectById(selectId) {
            const select = document.getElementById(selectId);
            if (!select) return;
            if (select.dataset.enhancedSearchable !== '1') {
                enhanceSearchableSelect(select);
            } else {
                renderEnhancedSearchableOptions(select);
            }
        }

        function showLineByIndex(index, shouldScroll = true) {
            const cards = Array.from(document.querySelectorAll('.variant-box[data-line-index]'));
            if (!cards.length) return;

            const nextIndex = Math.max(0, Math.min(index, cards.length - 1));
            linePagerState.total = cards.length;
            linePagerState.activeIndex = nextIndex;

            cards.forEach((card, idx) => {
                card.classList.toggle('line-page-hidden', idx !== nextIndex);
            });

            const activeCard = cards[nextIndex];
            const activeKey = activeCard?.dataset.lineKey || '';

            if (isListening && activeProductId && activeKey && activeProductId !== activeKey) {
                resetListeningState();
            }

            const status = document.getElementById('line_page_status');
            if (status) {
                const lineTitle = activeCard?.dataset.lineTitle || '';
                status.innerText = `Line ${nextIndex + 1} / ${cards.length}${lineTitle ? ` - ${lineTitle}` : ''}`;
            }

            const prevBtn = document.getElementById('line_prev_btn');
            const nextBtn = document.getElementById('line_next_btn');
            if (prevBtn) prevBtn.disabled = nextIndex === 0;
            if (nextBtn) nextBtn.disabled = nextIndex === cards.length - 1;

            const select = document.getElementById('line_page_select');
            if (select) select.value = String(nextIndex);

            if (shouldScroll) {
                activeCard?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }

        function goToPrevLine() {
            showLineByIndex(linePagerState.activeIndex - 1);
        }

        function goToNextLine() {
            showLineByIndex(linePagerState.activeIndex + 1);
        }

        function initializeLinePager() {
            const cards = Array.from(document.querySelectorAll('.variant-box[data-line-index]'));
            const pager = document.getElementById('line_pager');
            if (!cards.length || !pager) return;

            pager.classList.remove('hidden');
            const select = document.getElementById('line_page_select');
            if (select && select.dataset.bound !== '1') {
                select.addEventListener('change', (event) => {
                    const idx = parseInt(event.target.value, 10);
                    if (!Number.isNaN(idx)) {
                        showLineByIndex(idx);
                    }
                });
                select.dataset.bound = '1';
            }

            showLineByIndex(0, false);
        }

        // REQUIREMENT 1: Sync global parameters to hidden local forms dynamically
        function syncGlobalLotToInputs() {
            const val = document.getElementById('global_lot_name')?.value.trim() || '';
            document.querySelectorAll('[id^="incoming_lot_input_"]').forEach(el => {
                el.value = val;
            });
            document.querySelectorAll('[id^="global_lot_shadow_"]').forEach(el => {
                el.value = val;
            });
        }
        function syncGlobalOwnerToInputs() {
            const val = document.getElementById('global_owner_id')?.value || '';
            document.querySelectorAll('[id^="incoming_owner_input_"]').forEach(el => {
                el.value = val;
            });
            document.querySelectorAll('[id^="global_owner_shadow_"]').forEach(el => {
                el.value = val;
            });
        }

        function getActiveLotTarget(pId) {
            const isPurchaseMode = document.getElementById('global_lot_name') !== null;
            if (isPurchaseMode) {
                const poLotInput = document.getElementById('global_lot_name');
                return poLotInput ? poLotInput.value.trim() : '';
            }

            // OUT mode: this line scanner accepts only allocated lot prefixes.
            if (productLotAllocations[pId] && productLotAllocations[pId].length > 0) {
                return "__MULTI_LOT_MODE__";
            }

            return '';
        }

        function activateScanListeningSession(pId) {
            resetListeningState();
            const currentScroll = window.scrollY;
            const targetLot = getActiveLotTarget(pId);
            if (!targetLot) {
                myAlert('Action Blocked: Please configure global parameters or allocate a target warehouse lot row first.');
                return;
            }
            
            isListening = true;
            activeProductId = pId;
            if (!accumulatedTags[activeProductId]) {
                accumulatedTags[activeProductId] = [];
            }

            const scanInput = document.getElementById('live_scanner_input');
            const activationBtn = document.getElementById(`manual_activation_btn_${pId}`);
            const indicator = document.getElementById(`scanner_status_indicator_${pId}`);
            const pulseDot = document.getElementById(`pulse_dot_${pId}`);
            const statusText = document.getElementById(`status_text_${pId}`);
            
            if (scanInput) {
                scanInput.disabled = false;
                scanInput.value = '';
                try {
                    scanInput.focus({preventScroll: true});
                } catch (e) {
                    // Older browsers may not support preventScroll
                    scanInput.focus();
                    // attempt to restore scroll position
                    try { window.scrollTo(0, currentScroll); } catch (__) {}
                }
            }
            if (activationBtn) {
                activationBtn.style.background = 'var(--danger)';
                activationBtn.style.color = 'white';
                activationBtn.innerText = 'Listening - Scan Now';
            }
            if (indicator) {
                indicator.style.background = '#e6f6f6';
                indicator.style.borderColor = '#bce3e3';
            }
            if (pulseDot) {
                pulseDot.classList.add('dot-green');
            }
            if (statusText) {
                statusText.innerText = 'RUNNING';
            }
            setTimeout(() => {
        window.scrollTo(0, currentScroll);
    }, 50);
        }

        function resetListeningState() {
            isListening = false;
            const scanInput = document.getElementById('live_scanner_input');
            if (scanInput) {
                scanInput.value = '';
                scanInput.disabled = true;
            }

            if (activeProductId) {
                const pId = activeProductId;
                const activationBtn = document.getElementById(`manual_activation_btn_${pId}`);
                const indicator = document.getElementById(`scanner_status_indicator_${pId}`);
                const pulseDot = document.getElementById(`pulse_dot_${pId}`);
                const statusText = document.getElementById(`status_text_${pId}`);
                
                if (activationBtn) {
                    activationBtn.style.background = 'var(--surface-alt)';
                    activationBtn.style.color = 'var(--text)';
                    activationBtn.innerText = 'Initialize Scanner';
                }
                if (indicator) {
                    indicator.style.background = '#fff';
                    indicator.style.borderColor = 'var(--border)';
                }
                if (pulseDot) {
                    pulseDot.classList.remove('dot-green');
                }
                if (statusText) {
                    statusText.innerText = 'STANDBY';
                }
            }
            activeProductId = null;
        }

        function toggleScanTags(pId) {
            const box = document.getElementById(`scan_tags_collapse_${pId}`);
            if (!box) return;
            box.classList.toggle('open');
            updateScanToggleLabel(pId);
        }

        function updateScanToggleLabel(pId) {
            const btn = document.getElementById(`scan_tags_toggle_btn_${pId}`);
            if (!btn) return;
            const count = (accumulatedTags[pId] || []).length;
            const box = document.getElementById(`scan_tags_collapse_${pId}`);
            const isOpen = !!box && box.classList.contains('open');
            btn.innerText = `${isOpen ? 'Hide' : 'Tags'} (${count})`;
        }

        function toggleLotSummary(pId) {
            const box = document.getElementById(`lot_summary_collapse_${pId}`);
            if (!box) return;
            box.classList.toggle('open');
            updateLotSummaryToggleLabel(pId);
        }

        function updateLotSummaryToggleLabel(pId) {
            const btn = document.getElementById(`lot_summary_toggle_btn_${pId}`);
            if (!btn) return;
            const allocations = productLotAllocations[pId] || [];
            const totalScans = (accumulatedTags[pId] || []).length;
            const box = document.getElementById(`lot_summary_collapse_${pId}`);
            const isOpen = !!box && box.classList.contains('open');
            btn.innerText = `${isOpen ? 'Hide' : 'BL Details'} (${allocations.length}/${totalScans})`;
        }

        function getDemandQtyForLine(pId) {
            const demandEl = document.getElementById(`display_demand_${pId}`);
            return parseInt(demandEl?.innerText || '0', 10) || 0;
        }

        function getAllocatedTotalExcludingIndex(pId, excludedIndex = -1) {
            const list = productLotAllocations[pId] || [];
            let total = 0;
            list.forEach((item, idx) => {
                if (idx === excludedIndex) return;
                total += parseInt(item.allocated_qty, 10) || 0;
            });
            return total;
        }

        function renderTableGrid(pId) {
            const tbody = document.getElementById(`live_tag_tbody_${pId}`);
            if (!tbody) return;
            
            const tags = accumulatedTags[pId] || [];
            if (tags.length === 0) {
                tbody.innerHTML = '<div class="empty-state">No barcodes registered yet. Launch monitoring window above.</div>';
                document.getElementById(`tag_counter_${pId}`).innerText = '0';
                updateScanToggleLabel(pId);
                updateLotSummaryToggleLabel(pId);
                return;
            }
            tbody.innerHTML = '';
            tags.forEach((tag, index) => {
                const row = document.createElement('div');
                row.className = 'registry-row';
                row.innerHTML = `
                    <span class="text-muted small">${index + 1}</span>
                    <span class="tag-string">${tag}</span>
                    <button type="button" class="btn-row-remove" onclick="deleteRegistryRow('${pId}', ${index})">Del</button>
                `;
                tbody.appendChild(row);
            });
            document.getElementById(`tag_counter_${pId}`).innerText = tags.length.toString();
            updateScanToggleLabel(pId);
            updateLotSummaryToggleLabel(pId);
        }

        function myAlert(text) {
    // Non-blocking toast message (auto-dismisses) to avoid interrupting scanner flow
    const toast = document.createElement('div');
    toast.className = 'custom-toast';
    toast.textContent = text;
    toast.style.position = 'fixed';
    toast.style.right = '12px';
    toast.style.bottom = '12px';
    toast.style.background = 'rgba(0,0,0,0.8)';
    toast.style.color = 'white';
    toast.style.padding = '10px 14px';
    toast.style.borderRadius = '8px';
    toast.style.boxShadow = '0 6px 18px rgba(0,0,0,0.2)';
    toast.style.zIndex = 99999;
    toast.style.fontSize = '0.95rem';
    toast.style.maxWidth = '320px';
    toast.style.wordBreak = 'break-word';
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 180ms ease-in-out';

    toast.onclick = () => toast.remove();
    document.body.appendChild(toast);
    // fade in
    requestAnimationFrame(() => { toast.style.opacity = '1'; });
    // auto remove after 2.5s
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}
        function deleteRegistryRow(pId, index) {
            if (accumulatedTags[pId]) {
                accumulatedTags[pId].splice(index, 1);
            }
            renderTableGrid(pId);
            renderLotScanSummary(pId);
            if (isListening && activeProductId === pId) {
                document.getElementById('live_scanner_input')?.focus();
            }
        }

        // REQUIREMENT 2: Multi-Lot selection runtime injection handlers
        function addLotAllocationRow(pId) {
            const selectEl = document.getElementById(`lot_pool_select_${pId}`);
            if (!selectEl || !selectEl.value) return;
            
            if (!productLotAllocations[pId]) productLotAllocations[pId] = [];
            
            const selectedVal = selectEl.value; 
            // Check duplicates allocation
            if (productLotAllocations[pId].some(item => item.raw_value === selectedVal)) {
                myAlert("BL already allocated to this product.");
                return;
            }
            
            const selectedText = selectEl.options[selectEl.selectedIndex].text;
            const segments = selectedVal.split('|');
            const lotName = (segments[3] || '').trim();
            const maxAvailable = parseInt(segments[2], 10);
            const demandQty = getDemandQtyForLine(pId);
            const alreadyAllocated = getAllocatedTotalExcludingIndex(pId);
            const remainingDemand = Math.max(0, demandQty - alreadyAllocated);

            if (remainingDemand <= 0) {
                myAlert(`Cannot add more BL. Quantity already reached demand (${demandQty}).`);
                return;
            }
            
            productLotAllocations[pId].push({
                raw_value: selectedVal,
                lot_name: lotName,
                display_label: selectedText,
                max_qty: maxAvailable,
                allocated_qty: 1
            });
            
            renderAllocationTable(pId);
            renderLotScanSummary(pId);
        }

        function removeLotAllocationRow(pId, index) {
            if (productLotAllocations[pId]) {
                productLotAllocations[pId].splice(index, 1);
            }
            renderAllocationTable(pId);
            renderLotScanSummary(pId);
        }

        function updateAllocationQty(pId, index, inputEl) {
            let val = parseInt(inputEl.value, 10);
            if (isNaN(val) || val < 1) val = 1;
            
            const allocation = productLotAllocations[pId][index];
            const demandQty = getDemandQtyForLine(pId);
            const allocatedOtherLines = getAllocatedTotalExcludingIndex(pId, index);
            const maxByDemand = Math.max(0, demandQty - allocatedOtherLines);
            const hardMax = Math.min(allocation.max_qty, maxByDemand);

            if (hardMax <= 0) {
                myAlert('No remaining demand quantity. Remove another BL line or reduce its qty first.');
                removeLotAllocationRow(pId, index);
                return;
            }

            if (val > hardMax) {
                myAlert(`Cannot exceed... This line is limited by available stock and remaining demand.`);
                val = hardMax;
                inputEl.value = String(val);
            }
            
            productLotAllocations[pId][index].allocated_qty = val;
            calculateAllocatedSum(pId);
            renderLotScanSummary(pId);
        }
        function checkAllLinesSaved() {
    const allLines = document.querySelectorAll('[id^="variant_container_"]');
    const savedLines = document.querySelectorAll('[id^="variant_container_"].is-saved');
    const validateBtn = document.querySelector('.btn-accent'); // Target your 'Final Validate' button

    if (validateBtn) {
        // Show button only if ALL lines are saved
        if (savedLines.length === allLines.length && allLines.length > 0) {
            validateBtn.style.display = 'block';
        } else {
            validateBtn.style.display = 'none';
        }
    }
}

// Run once on page load to hide the button initially
document.addEventListener('DOMContentLoaded', checkAllLinesSaved);

        function markLineAsDone(pId) {
    const container = document.getElementById(`variant_container_${pId}`);
    if (container) {
        container.style.display = 'none'; // Hide the line
        container.classList.add('is-saved'); // Mark it as saved for the validation check
        checkAllLinesSaved(); // Update the Validate button
    }
}

        function renderAllocationTable(pId) {
            const container = document.getElementById(`allocation_container_${pId}`);
            if (!container) return;

            const list = productLotAllocations[pId] || [];
            if (list.length === 0) {
                container.innerHTML = '<div class="empty-state" style="padding:0.5rem;">No BL allocated yet. Choose options above.</div>';
                calculateAllocatedSum(pId);
                renderLotScanSummary(pId);
                return;
            }
    
            container.innerHTML = '';
            list.forEach((alloc, idx) => {
            const demandQty = getDemandQtyForLine(pId);
            const allocatedOtherLines = getAllocatedTotalExcludingIndex(pId, idx);
            const maxByDemand = Math.max(1, demandQty - allocatedOtherLines);
            const inputMax = Math.min(alloc.max_qty, maxByDemand);
        
            const div = document.createElement('div');
            // We use ONE unified class for perfect alignment
            div.className = 'allocation-row-card'; 
        
            div.innerHTML = `
            <!-- 1. BL Column -->
            <div class="lot-label" title="${alloc.display_label}">
                BL-${alloc.lot_name}
            </div>

            <!-- 2. QTY Column (Clean, no extra labels) -->
            <div class="qty-row">
                <input type="number" 
                       class="allocation-input" 
                       value="${alloc.allocated_qty}" 
                       min="1" 
                       max="${inputMax}" 
                       step="1" 
                       inputmode="numeric" 
                       onchange="updateAllocationQty('${pId}', ${idx}, this)">
            </div>

            <!-- 3. ACTION Column (Simple text) -->
            <div class="delete-row">
                <button type="button" 
                        class="remove-btn" 
                        onclick="removeLotAllocationRow('${pId}', ${idx})">
                    Remove
                </button>
            </div>
            `;
            container.appendChild(div);
            });
    
            calculateAllocatedSum(pId);
            renderLotScanSummary(pId);
        }


        function calculateAllocatedSum(pId) {
            const list = productLotAllocations[pId] || [];
            let total = 0;
            list.forEach(i => total += i.allocated_qty);
            
            const totalLbl = document.getElementById(`allocated_total_lbl_${pId}`);
            if (totalLbl) totalLbl.innerText = total.toString();
            return total;
        }

        function queryDeliveryQuants(pId) {
            const quantSelect = document.getElementById(`lot_pool_select_${pId}`);
            if (!quantSelect) return;
            const productId = quantSelect.dataset.productId;
            if (!productId) return;
            
            fetch(`/api/get-available-stock?product_id=${productId}`)
                .then((response) => response.json())
                .then((quants) => {
                    if (!Array.isArray(quants) || quants.length === 0) {
                        quantSelect.innerHTML = '<option value="">⚠️ No active BL stock available for this item</option>';
                        productAvailableLotsPool[pId] = [];
                        refreshSearchableSelectById(`lot_pool_select_${pId}`);
                        return;
                    }
                    productAvailableLotsPool[pId] = quants;
                    quantSelect.innerHTML = '<option value="">-- Choose Target BL Allocation Option --</option>';
                    quants.forEach((q) => {
                        const qty = parseInt(q.quantity, 10) || 0;
                        const lotName = (q.lot_name || '').trim();
                        const locationName = (q.location_name || '').trim();
                        const compactLabel = `BL-${lotName} | Available QTY ${qty}`;
                        const fullLabel = locationName ? `${compactLabel} | ${locationName}` : compactLabel;

                        const opt = document.createElement('option');
                        opt.value = `${q.lot_id}|${q.location_id}|${q.quantity}|${q.lot_name}|${q.owner_id}`;
                        opt.textContent = compactLabel;
                        opt.title = fullLabel;
                        quantSelect.appendChild(opt);
                    });
                    refreshSearchableSelectById(`lot_pool_select_${pId}`);
                })
                .catch((err) => {
                    quantSelect.innerHTML = '<option value="">❌ Error querying database lines</option>';
                    refreshSearchableSelectById(`lot_pool_select_${pId}`);
                });
        }

        function getTagPrefix(rawTag) {
            if (rawTag.includes(',')) {
                return rawTag.split(',')[0].trim();
            }
            return rawTag.trim();
        }

        function getTagsForLot(pId, lotName) {
            const tags = accumulatedTags[pId] || [];
            return tags.filter(tag => getTagPrefix(tag) === lotName);
        }

        function renderLotScanSummary(pId) {
            const panel = document.getElementById(`lot_scan_summary_${pId}`);
            if (!panel) return;

            const allocations = productLotAllocations[pId] || [];
            if (allocations.length === 0) {
                panel.innerHTML = '<div class="empty-state" style="padding:0.5rem;">Per-lot scan list will appear here after scans.</div>';
                updateLotSummaryToggleLabel(pId);
                return;
            }

            panel.innerHTML = '';
            allocations.forEach((alloc) => {
                const lotTags = getTagsForLot(pId, alloc.lot_name);
                const listPreview = lotTags.slice(0, 4).join(' | ');
                const extra = lotTags.length > 4 ? ` | +${lotTags.length - 4} more` : '';
                const row = document.createElement('div');
                row.className = 'lot-scan-summary-row';
                row.innerHTML = `
                    <div class="lot-scan-summary-head">
                        <span>BL-${alloc.lot_name}</span>
                        <span>${lotTags.length} / ${alloc.allocated_qty}</span>
                    </div>
                    <div class="lot-scan-summary-tags">${listPreview || 'No scans yet'}${extra}</div>
                `;
                panel.appendChild(row);
            });
            updateLotSummaryToggleLabel(pId);
        }

        function compileTagsBeforeSubmit(event, pId) {
            const scanInput = document.getElementById('live_scanner_input');
            if (scanInput) {
                scanInput.value = '';
            }

            const tags = accumulatedTags[pId] || [];
            const scannedQty = tags.length;
            const demandQty = parseInt(document.getElementById(`display_demand_${pId}`).innerText, 10);

            if (scannedQty === 0) {
                event.preventDefault();
                myAlert('❌ Cannot draft update! Capture matching tag references into the hardware panel list first.');
                return false;
            }

            const isPurchaseMode = document.getElementById('global_lot_name') !== null;
            if (!isPurchaseMode) {
                const totalAllocated = calculateAllocatedSum(pId);
                if (totalAllocated !== demandQty) {
                    event.preventDefault();
                    myAlert(`❌ Allocation Mismatch: The total sum of lot quantities (${totalAllocated}) must equal demand (${demandQty}).`);
                    return false;
                }

                const allocations = productLotAllocations[pId] || [];
                if (allocations.length === 0) {
                    event.preventDefault();
                    myAlert('❌ Allocate at least one lot before saving this line.');
                    return false;
                }

                for (const alloc of allocations) {
                    const lotCount = getTagsForLot(pId, alloc.lot_name).length;
                    if (lotCount !== alloc.allocated_qty) {
                        event.preventDefault();
                        myAlert(`❌ Lot ${alloc.lot_name} mismatch: scanned ${lotCount}, allocated ${alloc.allocated_qty}.`);
                        return false;
                    }
                }

                const serializedAllocations = allocations.map(a => `${a.raw_value}:${a.allocated_qty}`).join(';;');
                document.getElementById(`quant_selection_${pId}`).value = serializedAllocations;
            } else {
                syncGlobalLotToInputs();
                syncGlobalOwnerToInputs();

                const localLot = document.getElementById(`incoming_lot_input_${pId}`).value;
                const localLoc = document.getElementById(`incoming_loc_input_${pId}`).value;
                const localOwner = document.getElementById(`incoming_owner_input_${pId}`).value;

                if (!localOwner) {
                    event.preventDefault();
                    myAlert('❌ Missing global owner: choose one owner for all IN items.');
                    return false;
                }

                if (!localLoc) {
                    event.preventDefault();
                    myAlert('❌ Missing destination location for this IN item.');
                    return false;
                }

                if (!localLot) {
                    event.preventDefault();
                    myAlert('❌ Missing global lot: enter one lot for all IN items.');
                    return false;
                }
            }

            if (scannedQty !== demandQty) {
                event.preventDefault();
                myAlert(`❌ Read count mismatch: scanned ${scannedQty}, required ${demandQty}.`);
                return false;
            }

            document.getElementById(`explicit_clean_qty_${pId}`).value = scannedQty.toString();
            document.getElementById(`scanned_tags_csv_${pId}`).value = tags.join(',');
            return true;
        }

        // REQUIREMENT 3: Update local intermediate records draft trigger confirmation handler
        async function saveDraftLine(event, pId) {
    event.preventDefault();
    
    // 1. Prepare data
    const compiledStatus = compileTagsBeforeSubmit(event, pId);
    if (!compiledStatus) return false;

    const tags = accumulatedTags[pId] || [];
    const scannedQty = tags.length;
    
    // 2. Ask for confirmation
    const confirmed = confirm(
        `📋 SAVE INTERMEDIATE LINE DRAFT\n\n` +
        `✓ Scanned Target: ${scannedQty} items configured.\n\n` +
        `Click OK to store this item's structural parameters as local draft.`
    );

    if (confirmed) {
        const form = document.getElementById(`form_prod_${pId}`);
        const formData = new FormData(form);

        try {
            // 3. Send data in the background (AJAX)
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            if (response.ok) {
                // Attempt to parse JSON response from backend (safer for AJAX)
                let payload = null;
                try {
                    payload = await response.json();
                } catch (err) {
                    // Non-JSON response — assume success when HTTP OK
                    payload = { success: true, message: null };
                }

                if (payload && payload.success) {
                    // 4. Success: Hide the line and update Validate button
                    markLineAsDone(pId);
                    console.log(`Line ${pId} saved successfully.`);
                } else {
                    const msg = payload && payload.message ? `❌ ${payload.message}` : "❌ Server Error: Could not save the line draft.";
                    myAlert(msg);
                }
            } else {
                myAlert("❌ Server Error: Could not save the line draft.");
            }
        } catch (error) {
            console.error("Fetch error:", error);
            myAlert("❌ Connection Error: Failed to reach the server.");
        }
    }
    return false;
}

        // REQUIREMENT 3: Master explicit document confirmation configuration engine
        function confirmFinalDocumentValidation(event) {
            const confirmed = confirm(
                "⚠️ EXPLICIT COMPLETE TRANSFER DISPATCH\\n\\n" +
                "Are you sure you want to perform final execution validation parameters on this open sheet document?\\n\\n" +
                "This action commits total operations rows permanently and pushes stock into inventory accounts."
            );
            if (!confirmed) {
                event.preventDefault();
                return false;
            }
            return true;
        }

        window.addEventListener('DOMContentLoaded', () => {
            initializeSearchableSelects();
            initializeCustomSelects();
            closeAllCustomSelects();
            window.addEventListener('resize', repositionOpenDropdowns);
            window.addEventListener('scroll', repositionOpenDropdowns, true);

            if (document.getElementById('global_lot_name')) {
                syncGlobalLotToInputs();
                syncGlobalOwnerToInputs();
            }

            document.querySelectorAll('[id^="lot_pool_select_"]').forEach(el => {
                const pId = el.id.replace('lot_pool_select_', '');
                queryDeliveryQuants(pId);
                renderLotScanSummary(pId);
            });

            document.querySelectorAll('[id^="live_tag_tbody_"]').forEach((el) => {
                const pId = el.id.replace('live_tag_tbody_', '');
                updateScanToggleLabel(pId);
            });

            initializeLinePager();

            const scanInput = document.getElementById('live_scanner_input');
            if (!scanInput) return;
            
            window.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' && event.target === scanInput) {
                    event.preventDefault();
                }
            });
            
            document.addEventListener('click', (event) => {
                if (!isListening) return;
                if (!['BUTTON', 'INPUT', 'SELECT', 'OPTION', 'TEXTAREA'].includes(event.target.tagName)) {
                    scanInput.focus();
                }
            });
            
            scanInput.addEventListener('keyup', (event) => {
                if (event.key !== 'Enter') return;
                event.preventDefault();
                
                const rawTag = scanInput.value.trim();
                scanInput.value = '';
                
                if (!isListening || !activeProductId || rawTag.length === 0) return;
                
                const pId = activeProductId;
                if (!accumulatedTags[pId]) accumulatedTags[pId] = [];
                
                const demandQty = parseInt(document.getElementById(`display_demand_${pId}`).innerText, 10);
                
                if (accumulatedTags[pId].length >= demandQty) {
                    myAlert(`⚠️ Limit reached! Total required target volume metrics accomplished (${demandQty} units).`);
                    scanInput.focus({preventScroll: true});
                    return;
                }

                const targetLotToken = getActiveLotTarget(pId);
                const parsedPrefix = getTagPrefix(rawTag);
                
                if (accumulatedTags[pId].includes(rawTag)) {
                    // ignore duplicates but keep focus
                    scanInput.focus({preventScroll: true});
                    return;
                }
                
                if (targetLotToken === "__MULTI_LOT_MODE__") {
                    const assignedLots = productLotAllocations[pId] || [];
                    const matchedLot = assignedLots.find(a => a.lot_name === parsedPrefix);
                    if (!matchedLot) {
                        myAlert(`❌ This scan belongs to lot ${parsedPrefix}, which is not allocated for this line.`);
                        scanInput.focus({preventScroll: true});
                        return;
                    }

                    const currentLotCount = getTagsForLot(pId, parsedPrefix).length;
                    if (currentLotCount >= matchedLot.allocated_qty) {
                        myAlert(`❌ Lot ${parsedPrefix} already reached allocated quantity (${matchedLot.allocated_qty}).`);
                        scanInput.focus({preventScroll: true});
                        return;
                    }

                    accumulatedTags[pId].push(rawTag);
                    renderTableGrid(pId);
                    renderLotScanSummary(pId);
                    scanInput.focus({preventScroll: true});
                } else if (parsedPrefix === targetLotToken) {
                    accumulatedTags[pId].push(rawTag);
                    renderTableGrid(pId);
                    scanInput.focus({preventScroll: true});
                }
            });

            if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                    navigator.serviceWorker.register('/sw.js').catch(() => {});
                });
            }
        });
    </script>
</body>
</html>"""

# =====================================================================
# BACKEND - ODOO CLIENT
# =====================================================================

def verify_and_get_client(odoo_url, db_name, email, api_key):
    """Authenticate and return authenticated models proxy and user ID"""
    try:
        common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
        models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')
        uid = common.authenticate(db_name, email, api_key, {})
        if uid:
            return models, uid
        return None, None
    except Exception:
        return None, None


# =====================================================================
# BACKEND - BUSINESS LOGIC & DATA ACCESS (REQUIREMENT 4 CACHE UPGRADED)
# =====================================================================

def get_filtered_documents(models, uid, api_key, db_name, mode):
    """Retrieve purchase orders or sales orders with open pickings"""
    current_timestamp = time.time()
    cache_key = _cache_key(db_name, mode=mode)
    if (cache_key in GLOBAL_PERFORMANCE_CACHE['documents'] and
            current_timestamp < GLOBAL_PERFORMANCE_CACHE['documents_expiry'].get(cache_key, 0)):
        return GLOBAL_PERFORMANCE_CACHE['documents'][cache_key]

    if mode == 'purchase':
        open_pickings = models.execute_kw(
            db_name, uid, api_key, 'stock.picking', 'search_read',
            [[['picking_type_code', '=', 'incoming'], ['state', 'not in', ['done', 'cancel']]]],
            {'fields': ['purchase_id']}
        )
        po_ids = list(set([p['purchase_id'][0] for p in open_pickings if p.get('purchase_id')]))
        if not po_ids:
            GLOBAL_PERFORMANCE_CACHE['documents'][cache_key] = []
            GLOBAL_PERFORMANCE_CACHE['documents_expiry'][cache_key] = current_timestamp + DOC_CACHE_TTL
            return []
        data = models.execute_kw(
            db_name, uid, api_key, 'purchase.order', 'search_read',
            [[['id', 'in', po_ids]]],
            {'fields': ['id', 'name', 'partner_id'], 'order': 'name desc', 'limit': 40}
        )
        GLOBAL_PERFORMANCE_CACHE['documents'][cache_key] = data
        GLOBAL_PERFORMANCE_CACHE['documents_expiry'][cache_key] = current_timestamp + DOC_CACHE_TTL
        return data
    else:
        open_pickings = models.execute_kw(
            db_name, uid, api_key, 'stock.picking', 'search_read',
            [[['picking_type_code', '=', 'outgoing'], ['state', 'not in', ['done', 'cancel']]]],
            {'fields': ['sale_id']}
        )
        so_ids = list(set([p['sale_id'][0] for p in open_pickings if p.get('sale_id')]))
        if not so_ids:
            GLOBAL_PERFORMANCE_CACHE['documents'][cache_key] = []
            GLOBAL_PERFORMANCE_CACHE['documents_expiry'][cache_key] = current_timestamp + DOC_CACHE_TTL
            return []
        data = models.execute_kw(
            db_name, uid, api_key, 'sale.order', 'search_read',
            [[['id', 'in', so_ids]]],
            {'fields': ['id', 'name', 'partner_id'], 'order': 'name desc', 'limit': 40}
        )
        GLOBAL_PERFORMANCE_CACHE['documents'][cache_key] = data
        GLOBAL_PERFORMANCE_CACHE['documents_expiry'][cache_key] = current_timestamp + DOC_CACHE_TTL
        return data


def get_internal_locations(models, uid, api_key, db_name):
    """REQUIREMENT 4: Cache-backed ultra-fast internal stock locations fetch routing"""
    current_timestamp = time.time()
    if (GLOBAL_PERFORMANCE_CACHE['locations'] is not None and 
            current_timestamp < GLOBAL_PERFORMANCE_CACHE['locations_expiry']):
        return GLOBAL_PERFORMANCE_CACHE['locations']
        
    try:
        data = models.execute_kw(
            db_name, uid, api_key, 'stock.location', 'search_read',
            [[['usage', '=', 'internal']]],
            {'fields': ['id', 'complete_name'], 'order': 'complete_name asc'}
        )
        GLOBAL_PERFORMANCE_CACHE['locations'] = data
        GLOBAL_PERFORMANCE_CACHE['locations_expiry'] = current_timestamp + CACHE_TTL
        return data
    except Exception:
        return []


def get_partners(models, uid, api_key, db_name):
    """REQUIREMENT 4: Cache-backed performance optimized business partner fetch loops"""
    current_timestamp = time.time()
    if (GLOBAL_PERFORMANCE_CACHE['partners'] is not None and 
            current_timestamp < GLOBAL_PERFORMANCE_CACHE['partners_expiry']):
        return GLOBAL_PERFORMANCE_CACHE['partners']
        
    try:
        data = models.execute_kw(
            db_name, uid, api_key, 'res.partner', 'search_read',
            [[]],
            {'fields': ['id', 'name'], 'order': 'name asc'}
        )
        GLOBAL_PERFORMANCE_CACHE['partners'] = data
        GLOBAL_PERFORMANCE_CACHE['partners_expiry'] = current_timestamp + CACHE_TTL
        return data
    except Exception:
        return []


def get_available_stock(models, uid, api_key, db_name, product_id):
    """Retrieve available stock quants for a product with lot allocation"""
    current_timestamp = time.time()
    cache_key = _cache_key(db_name, product_id=product_id)
    if (cache_key in GLOBAL_PERFORMANCE_CACHE['available_stock'] and
            current_timestamp < GLOBAL_PERFORMANCE_CACHE['available_stock_expiry'].get(cache_key, 0)):
        return GLOBAL_PERFORMANCE_CACHE['available_stock'][cache_key]

    try:
        quants = models.execute_kw(
            db_name, uid, api_key, 'stock.quant', 'search_read',
            [[['product_id', '=', product_id], ['location_id.usage', '=', 'internal'], 
              ['quantity', '>', 0], ['lot_id', '!=', False]]],
            {'fields': ['lot_id', 'location_id', 'quantity', 'owner_id']}
        )
        results = []
        for q in quants:
            owner_id = q['owner_id'][0] if q.get('owner_id') else 0
            owner_name = q['owner_id'][1] if q.get('owner_id') else "No Owner"
            results.append({
                'lot_id': q['lot_id'][0],
                'lot_name': q['lot_id'][1],
                'location_id': q['location_id'][0],
                'location_name': q['location_id'][1],
                'quantity': q['quantity'],
                'owner_id': owner_id,
                'owner_name': owner_name
            })
        GLOBAL_PERFORMANCE_CACHE['available_stock'][cache_key] = results
        GLOBAL_PERFORMANCE_CACHE['available_stock_expiry'][cache_key] = current_timestamp + STOCK_CACHE_TTL
        return results
    except Exception as e:
        logging.error(f'get_available_stock error: {str(e)}')
        return []


def process_purchase_receipt(models, uid, api_key, db_name, doc_id, product_id,
                             move_id, final_validated_qty, new_lot_name,
                             target_location_id, owner_id_value):
    """Process purchase order receipt stage mapping records out as DRAFT items (REQUIREMENT 3 REMAPPED)"""
    try:
        picking_ids = models.execute_kw(
            db_name, uid, api_key, 'stock.picking', 'search',
            [[['purchase_id', '=', doc_id], ['state', 'not in', ['done', 'cancel']]]]
        )
        if not picking_ids:
            return False, "⚠️ Operation Error: Missing open transfer sheet."
        
        active_picking_id = picking_ids[0]
        company_ids = models.execute_kw(db_name, uid, api_key, 'res.company', 'search', [[]], {'limit': 1})
        comp_id = company_ids[0] if company_ids else 1
        
        if owner_id_value:
            models.execute_kw(
                db_name, uid, api_key, 'stock.picking', 'write',
                [[active_picking_id], {'owner_id': owner_id_value}]
            )
        
        active_move_id = int(move_id)
        
        picking_data = models.execute_kw(db_name, uid, api_key, 'stock.picking', 'read', [[active_picking_id]], {'fields': ['location_id']})[0]
        src_loc = picking_data['location_id'][0]
        dest_loc = int(target_location_id)
        
        existing_line_ids = models.execute_kw(
            db_name, uid, api_key, 'stock.move.line', 'search',
            [[['move_id', '=', active_move_id], ['product_id', '=', product_id]]]
        )

        lot_search = models.execute_kw(
            db_name, uid, api_key, 'stock.lot', 'search',
            [[['name', '=', new_lot_name], ['product_id', '=', product_id]]]
        )
        lot_id = lot_search[0] if lot_search else models.execute_kw(
            db_name, uid, api_key, 'stock.lot', 'create',
            [{'name': new_lot_name, 'product_id': product_id, 'company_id': comp_id}]
        )

        payload = {
            'picking_id': active_picking_id,
            'move_id': active_move_id,
            'product_id': product_id,
            'lot_id': lot_id,
            'quantity': final_validated_qty,
            'location_id': src_loc,
            'location_dest_id': dest_loc,
            'owner_id': owner_id_value,
        }

        if existing_line_ids:
            models.execute_kw(db_name, uid, api_key, 'stock.move.line', 'write', [[existing_line_ids[0]], payload])
            if len(existing_line_ids) > 1:
                models.execute_kw(db_name, uid, api_key, 'stock.move.line', 'unlink', [existing_line_ids[1:]])
        else:
            models.execute_kw(db_name, uid, api_key, 'stock.move.line', 'create', [payload])
        
        return True, f"📋 Intermediate draft changes applied onto product move records."
        
    except Exception as e:
        tb = traceback.format_exc()
        logging.error(tb)
        return False, f"Odoo Core Error: {str(e)}"


def process_delivery_shipment(models, uid, api_key, db_name, doc_id, product_id,
                              move_id, final_validated_qty, quant_selection):
    """Process multi-lot sales order delivery modifications safely as lines payload split arrays (REQUIREMENT 2 & 3)"""
    try:
        picking_ids = models.execute_kw(
            db_name, uid, api_key, 'stock.picking', 'search',
            [[['sale_id', '=', doc_id], ['state', 'not in', ['done', 'cancel']]]]
        )
        if not picking_ids:
            return False, "⚠️ Operation Error: Missing open transfer sheet."
        
        active_picking_id = picking_ids[0]
        
        active_move_id = int(move_id)
        
        picking_data = models.execute_kw(db_name, uid, api_key, 'stock.picking', 'read', [[active_picking_id]], {'fields': ['location_dest_id']})[0]
        dest_loc = picking_data['location_dest_id'][0]
        
        # Clear out prior existing lines mapped against this active item move to prevent overlapping constraints tracking
        old_line_ids = models.execute_kw(
            db_name, uid, api_key, 'stock.move.line', 'search',
            [[['move_id', '=', active_move_id], ['product_id', '=', product_id]]]
        )
        if old_line_ids:
            models.execute_kw(db_name, uid, api_key, 'stock.move.line', 'unlink', [old_line_ids])

        # Parse allocation structures matrix: "lot_id|loc_id|max|name|owner:qty;;lot_id|..."
        allocation_blocks = quant_selection.split(';;')
        for block in allocation_blocks:
            if not block:
                continue
            meta_string, split_qty_str = block.split(':')
            split_qty = float(split_qty_str)
            
            lot_id_str, src_location_str, _, _, raw_owner_id = meta_string.split('|')
            lot_id = int(lot_id_str)
            src_loc = int(src_location_str)
            owner_id_value = int(raw_owner_id) if int(raw_owner_id) > 0 else False
            
            if owner_id_value:
                models.execute_kw(db_name, uid, api_key, 'stock.picking', 'write', [[active_picking_id], {'owner_id': owner_id_value}])
                
            payload = {
                'picking_id': active_picking_id,
                'move_id': active_move_id,
                'product_id': product_id,
                'lot_id': lot_id,
                'quantity': split_qty,
                'location_id': src_loc,
                'location_dest_id': dest_loc,
                'owner_id': owner_id_value,
            }
            models.execute_kw(db_name, uid, api_key, 'stock.move.line', 'create', [payload])
            
        return True, f"📋 Saved intermediate multi-lot allocation matrix rules onto transfer item records."
        
    except Exception as e:
        tb = traceback.format_exc()
        logging.error(tb)
        return False, f"Odoo Core Error: {str(e)}"


# =====================================================================
# ROUTES
# =====================================================================

@app.route('/manifest.webmanifest')
def web_manifest():
    manifest = {
        'id': '/?source=pwa',
        'name': 'VTHC Middleware',
        'short_name': 'VTHC',
        'description': 'RFID middleware bridge for Odoo inventory operations',
        'lang': 'en',
        'dir': 'ltr',
        'start_url': '/',
        'scope': '/',
        'orientation': 'portrait',
        'display': 'standalone',
        'display_override': ['standalone', 'minimal-ui', 'browser'],
        'background_color': '#f5f6fa',
        'theme_color': '#714b67',
        'categories': ['business', 'productivity', 'utilities'],
        'prefer_related_applications': False,
        'related_applications': [],
        'icons': [
            {
                'src': '/icon-192.png',
                'sizes': '192x192',
                'type': 'image/png',
                'purpose': 'any maskable'
            },
            {
                'src': '/icon-512.png',
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'any maskable'
            }
        ],
        'screenshots': [
            {
                'src': '/pwa-screenshot-portrait.png',
                'sizes': '1080x1920',
                'type': 'image/png',
                'label': 'VTHC Middleware mobile view',
                'form_factor': 'narrow'
            },
            {
                'src': '/pwa-screenshot-landscape.png',
                'sizes': '1920x1080',
                'type': 'image/png',
                'label': 'VTHC Middleware desktop view',
                'form_factor': 'wide'
            }
        ],
        'shortcuts': [
            {
                'name': 'Open Middleware',
                'short_name': 'Open',
                'url': '/'
            }
        ]
    }
    return Response(json.dumps(manifest), mimetype='application/manifest+json')


@app.route('/sw.js')
def service_worker():
    script = """
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

// Keep requests network-first to avoid stale inventory/session data.
self.addEventListener('fetch', () => {});
""".strip()
    response = Response(script, mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@app.route('/icon.svg')
def app_icon():
    svg = """
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'>
  <rect width='512' height='512' rx='96' fill='#714b67'/>
  <text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle'
        font-family='Arial, sans-serif' font-size='190' font-weight='700' fill='#ffffff'>V</text>
</svg>
""".strip()
    return Response(svg, mimetype='image/svg+xml')


def _build_png_image(width, height, heading, subheading=''):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new('RGB', (width, height), '#f5f6fa')
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, width, int(height * 0.2)), fill='#714b67')
    draw.rectangle((0, int(height * 0.2), width, int(height * 0.24)), fill='#00a09d')

    font_big = ImageFont.load_default()
    font_small = ImageFont.load_default()

    draw.text((int(width * 0.07), int(height * 0.08)), heading, fill='#ffffff', font=font_big)
    if subheading:
        draw.text((int(width * 0.07), int(height * 0.3)), subheading, fill='#253249', font=font_small)

    output = BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    return output.getvalue()


@app.route('/icon-192.png')
def app_icon_192_png():
    payload = _build_png_image(192, 192, 'VTHC')
    return Response(payload, mimetype='image/png')


@app.route('/icon-512.png')
def app_icon_512_png():
    payload = _build_png_image(512, 512, 'VTHC')
    return Response(payload, mimetype='image/png')


@app.route('/pwa-screenshot-portrait.png')
def pwa_screenshot_portrait():
    payload = _build_png_image(1080, 1920, 'VTHC Middleware', 'RFID workflow for Odoo inventory operations')
    return Response(payload, mimetype='image/png')


@app.route('/pwa-screenshot-landscape.png')
def pwa_screenshot_landscape():
    payload = _build_png_image(1920, 1080, 'VTHC Middleware', 'IN/OUT line processing with scanner support')
    return Response(payload, mimetype='image/png')

@app.route('/')
def dashboard():
    """Main dashboard route"""
    if 'user_email' not in session:
        return render_template_string(HTML_TEMPLATE, documents=[], message=None, msg_type=None)
    
    if 'mode' not in session:
        session['mode'] = 'purchase'

    models, uid = verify_and_get_client(
        session['odoo_url'], session['db_name'], session['user_email'], session['api_key']
    )
    if not uid:
        return redirect(url_for('logout'))

    locations = get_internal_locations(models, uid, session['api_key'], session['db_name'])
    partners = get_partners(models, uid, session['api_key'], session['db_name'])
    documents = get_filtered_documents(models, uid, session['api_key'], session['db_name'], session['mode'])

    return render_template_string(
        HTML_TEMPLATE,
        documents=documents,
        current_mode=session['mode'],
        locations=locations,
        partners=partners,
        selected_doc=None,
        products=[],
        selected_owner_id=None,
        message=None,
        msg_type=None
    )


@app.route('/api/get-available-stock')
def get_stock():
    """API endpoint to retrieve available stock for a product"""
    if 'user_email' not in session:
        return jsonify([])
    try:
        product_id = int(request.args.get('product_id', 0))
    except ValueError:
        return jsonify([])

    models, uid = verify_and_get_client(
        session['odoo_url'], session['db_name'], session['user_email'], session['api_key']
    )
    if not uid:
        return jsonify([])

    quants = get_available_stock(models, uid, session['api_key'], session['db_name'], product_id)
    return jsonify(quants)


@app.route('/switch-mode/<target_mode>')
def switch_mode(target_mode):
    """Switch between purchase (IN) and delivery (OUT) modes"""
    session['mode'] = target_mode
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    odoo_url = request.form.get('odoo_url', '').strip().rstrip('/')
    db_name = request.form.get('db_name', '').strip()
    email = request.form.get('email', '').strip()
    api_key = request.form.get('api_key', '').strip()

    models, uid = verify_and_get_client(odoo_url, db_name, email, api_key)
    if uid:
        session['odoo_url'] = odoo_url
        session['db_name'] = db_name
        session['user_email'] = email
        session['api_key'] = api_key
        session['mode'] = 'purchase'
        return redirect(url_for('dashboard'))
    
    return render_template_string(HTML_TEMPLATE, documents=[], message='Connection Failed!', msg_type='danger')


@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    return redirect(url_for('dashboard'))


@app.route('/select-doc', methods=['POST'])
def select_doc():
    """Select a document and load its uncompleted warehouse stock move lines"""
    if 'user_email' not in session:
        return redirect(url_for('dashboard'))
    
    doc_id = request.form.get('doc_id')
    if not doc_id:
        return redirect(url_for('dashboard'))

    models, uid = verify_and_get_client(
        session['odoo_url'], session['db_name'], session['user_email'], session['api_key']
    )
    if not uid:
        return redirect(url_for('logout'))

    documents = get_filtered_documents(models, uid, session['api_key'], session['db_name'], session['mode'])
    selected_doc = next((d for d in documents if d['id'] == int(doc_id)), None)
    
    products = []
    selected_owner_id = None
    if selected_doc:
        picking_domain = [['state', 'not in', ['done', 'cancel']]]
        if session['mode'] == 'purchase':
            picking_domain.append(['purchase_id', '=', int(doc_id)])
        else:
            picking_domain.append(['sale_id', '=', int(doc_id)])
            
        picking_ids = models.execute_kw(session['db_name'], uid, session['api_key'], 'stock.picking', 'search', [picking_domain], {'limit': 1})
        
        if picking_ids:
            active_picking_id = picking_ids[0]
            moves = models.execute_kw(
                session['db_name'], uid, session['api_key'], 'stock.move', 'search_read',
                [[['picking_id', '=', active_picking_id], ['state', 'not in', ['done', 'cancel']]]],
                {"fields": ["id", "product_id", "product_qty", "quantity"]}
            )
            
            for m in moves:
                demand = float(m['product_qty'])
                products.append({
                    'move_id': m['id'],
                    'line_key': str(m['id']),
                    'product_id': m['product_id'],
                    'product_qty': demand
                })

            picking_data = models.execute_kw(
                session['db_name'], uid, session['api_key'], 'stock.picking', 'read', 
                [[active_picking_id]], {'fields': ['owner_id']}
            )
            if picking_data and picking_data[0].get('owner_id'):
                selected_owner_id = picking_data[0]['owner_id'][0]

    locations = get_internal_locations(models, uid, session['api_key'], session['db_name'])
    partners = get_partners(models, uid, session['api_key'], session['db_name'])

    return render_template_string(
        HTML_TEMPLATE,
        documents=documents,
        selected_doc=selected_doc,
        products=products,
        current_mode=session['mode'],
        locations=locations,
        partners=partners,
        selected_owner_id=selected_owner_id,
        saved_lot_name=request.form.get('global_lot_name', ''),
        saved_location_id=request.form.get('global_location_id', ''),
        saved_owner_id=request.form.get('global_owner_id', ''),
        message=None,
        msg_type=None
    )


@app.route('/submit-sync', methods=['POST'])
def submit_sync():
    """Submit and validate RFID scanned variant row information"""
    if 'user_email' not in session:
        return redirect(url_for('dashboard'))

    doc_id = int(request.form.get('doc_id_raw', 0))
    product_id = int(request.form.get('product_id_raw', 0))
    move_id = int(request.form.get('move_id_raw', 0))
    final_validated_qty = float(request.form.get('explicit_clean_qty', 0))

    models, uid = verify_and_get_client(
        session['odoo_url'], session['db_name'], session['user_email'], session['api_key']
    )
    if not uid:
        return redirect(url_for('logout'))

    if session['mode'] == 'purchase':
        new_lot_name = request.form.get('lot_name', '').strip()
        target_location_id = int(request.form.get('location_id', 0))
        assigned_owner_id = request.form.get('owner_id', '')
        owner_id_value = int(assigned_owner_id) if assigned_owner_id else False
        
        success, message = process_purchase_receipt(
            models, uid, session['api_key'], session['db_name'],
            doc_id, product_id, move_id, final_validated_qty,
            new_lot_name, target_location_id, owner_id_value
        )
    else:
        quant_selection = request.form.get('quant_selection', '')
        success, message = process_delivery_shipment(
            models, uid, session['api_key'], session['db_name'],
            doc_id, product_id, move_id, final_validated_qty, quant_selection
        )

    if success:
        invalidate_runtime_cache()

    # If this was an AJAX request from the client, return a lightweight JSON result
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    documents = get_filtered_documents(models, uid, session['api_key'], session['db_name'], session['mode'])
    selected_doc = next((d for d in documents if d['id'] == doc_id), None)
    
    products = []
    selected_owner_id = None
    if selected_doc:
        picking_domain = [['state', 'not in', ['done', 'cancel']]]
        picking_domain.append(['purchase_id' if session['mode'] == 'purchase' else 'sale_id', '=', doc_id])
        picking_ids = models.execute_kw(session['db_name'], uid, session['api_key'], 'stock.picking', 'search', [picking_domain], {'limit': 1})
        if picking_ids:
            moves = models.execute_kw(
                session['db_name'], uid, session['api_key'], 'stock.move', 'search_read',
                [[['picking_id', '=', picking_ids[0]], ['state', 'not in', ['done', 'cancel']]]],
                {'fields': ['product_id', 'product_qty', 'quantity']}
            )
            
            products = [{
                'move_id': m['id'],
                'line_key': str(m['id']),
                'product_id': m['product_id'], 
                'product_qty': float(m['product_qty'])
            } for m in moves]

            picking_data = models.execute_kw(
                session['db_name'], uid, session['api_key'], 'stock.picking', 'read', 
                [[picking_ids[0]]], {'fields': ['owner_id']}
            )
            if picking_data and picking_data[0].get('owner_id'):
                selected_owner_id = picking_data[0]['owner_id'][0]

    locations = get_internal_locations(models, uid, session['api_key'], session['db_name'])
    partners = get_partners(models, uid, session['api_key'], session['db_name'])

    return render_template_string(
        HTML_TEMPLATE,
        documents=documents,
        selected_doc=selected_doc,
        products=products,
        current_mode=session['mode'],
        locations=locations,
        partners=partners,
        selected_owner_id=selected_owner_id,
        saved_lot_name=request.form.get('global_lot_name', request.form.get('lot_name', '')),
        saved_location_id=request.form.get('location_id', ''),
        saved_owner_id=request.form.get('global_owner_id', request.form.get('owner_id', '')),
        message=message,
        msg_type='success' if success else 'danger'
    )


# =====================================================================
# REQUIREMENT 3: Core document final explicit validation routing controller
# =====================================================================
@app.route('/validate-document-complete', methods=['POST'])
def validate_document_complete():
    """Trigger master validation workflow parameters permanently against open Odoo transfer pickings"""
    if 'user_email' not in session:
        return redirect(url_for('dashboard'))
        
    doc_id = int(request.form.get('final_doc_id', 0))
    if not doc_id:
        return redirect(url_for('dashboard'))
        
    models, uid = verify_and_get_client(
        session['odoo_url'], session['db_name'], session['user_email'], session['api_key']
    )
    if not uid:
        return redirect(url_for('logout'))
        
    try:
        picking_domain = [['state', 'not in', ['done', 'cancel']]]
        picking_domain.append(['purchase_id' if session['mode'] == 'purchase' else 'sale_id', '=', doc_id])
        picking_ids = models.execute_kw(session['db_name'], uid, session['api_key'], 'stock.picking', 'search', [picking_domain], {'limit': 1})
        
        if not picking_ids:
            return redirect(url_for('dashboard'))
            
        active_picking_id = picking_ids[0]
        
        # Execute automated validation on Odoo backend workflows layers
        validation_result = models.execute_kw(session['db_name'], uid, session['api_key'], 'stock.picking', 'button_validate', [[active_picking_id]])
        invalidate_runtime_cache()
        
        message = "🎉 Entire warehouse sheet validated and confirmed automatically to Odoo registry database!"
        msg_type = "success"
    except Exception as e:
        message = f"Odoo Core Processing Validation Exception Error: {str(e)}"
        msg_type = "danger"
        
    return render_template_string(
        HTML_TEMPLATE,
        documents=get_filtered_documents(models, uid, session['api_key'], session['db_name'], session['mode']),
        current_mode=session['mode'],
        locations=get_internal_locations(models, uid, session['api_key'], session['db_name']),
        partners=get_partners(models, uid, session['api_key'], session['db_name']),
        selected_doc=None,
        products=[],
        selected_owner_id=None,
        message=message,
        msg_type=msg_type
    )


def run_flask_server(host='127.0.0.1', port=5000):
    """Start the Flask middleware server from an Android native wrapper."""
    preferred_port = int(os.environ.get('MIDDLEWARE_PORT', str(port)))
    try:
        app.run(host=host, port=preferred_port, debug=False, threaded=True)
    except OSError:
        fallback_port = 5001 if preferred_port == 5000 else 5000
        logging.warning(f'Port {preferred_port} unavailable, starting on {fallback_port}')
        app.run(host=host, port=fallback_port, debug=False, threaded=True)


if __name__ == '__main__':
    run_flask_server()