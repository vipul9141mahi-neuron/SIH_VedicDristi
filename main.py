# main.py - Flask application for Herb Authentication Chatbot
from flask import Flask, render_template, request, jsonify
import hashlib
import json
import datetime
import qrcode
import io
import base64
from PIL import Image
import sqlite3

app = Flask(__name__)

# Simple Blockchain Implementation
class HerbBlock:
    def __init__(self, index, timestamp, data, previous_hash=''):
        self.index = index
        self.timestamp = timestamp
        self.data = data  # farmer data: name, herb, location, season, cost
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.timestamp}{json.dumps(self.data)}{self.previous_hash}"
        return hashlib.sha256(block_string.encode()).hexdigest()

class HerbBlockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return HerbBlock(0, datetime.datetime.now().isoformat(), 
                        {"message": "Genesis Block for Herb Authentication"}, "0")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, herb_data):
        previous_block = self.get_latest_block()
        new_block = HerbBlock(
            len(self.chain),
            datetime.datetime.now().isoformat(),
            herb_data,
            previous_block.hash
        )
        self.chain.append(new_block)
        return new_block

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False
        return True

# Initialize blockchain
herb_blockchain = HerbBlockchain()

# Database setup
def init_db():
    conn = sqlite3.connect('herbs.db')
    c = conn.cursor()
    create_table_sql = """CREATE TABLE IF NOT EXISTS farmer_data
                 (id INTEGER PRIMARY KEY, 
                  farmer_name TEXT, 
                  herb_type TEXT, 
                  location TEXT, 
                  season TEXT, 
                  cost_per_kg REAL, 
                  block_hash TEXT, 
                  qr_code TEXT,
                  timestamp TEXT)"""
    c.execute(create_table_sql)
    conn.commit()
    conn.close()

def generate_qr_code(data):
    """Generate QR code for herb data"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64 for web display
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{img_base64}"

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/api/submit_herb_data', methods=['POST'])
def submit_herb_data():
    try:
        data = request.json

        # Create herb data object
        herb_data = {
            'farmer_name': data['farmer_name'],
            'herb_type': data['herb_type'],
            'location': data['location'],
            'season': data['season'],
            'cost_per_kg': float(data['cost_per_kg']),
            'submission_time': datetime.datetime.now().isoformat()
        }

        # Add to blockchain
        new_block = herb_blockchain.add_block(herb_data)

        # Generate unique QR code
        qr_data = {
            'block_hash': new_block.hash,
            'herb_info': herb_data['herb_type'],
            'farmer': herb_data['farmer_name'],
            'verify_url': f"https://your-app.replit.dev/verify/{new_block.hash}"
        }

        qr_code_img = generate_qr_code(json.dumps(qr_data))

        # Save to database
        conn = sqlite3.connect('herbs.db')
        c = conn.cursor()
        insert_sql = """INSERT INTO farmer_data 
                    (farmer_name, herb_type, location, season, cost_per_kg, 
                     block_hash, qr_code, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        c.execute(insert_sql,
                 (herb_data['farmer_name'], herb_data['herb_type'], 
                  herb_data['location'], herb_data['season'], 
                  herb_data['cost_per_kg'], new_block.hash, 
                  qr_code_img, herb_data['submission_time']))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Herb data successfully recorded on blockchain!',
            'block_hash': new_block.hash,
            'qr_code': qr_code_img,
            'unique_id': new_block.hash[:8]  # Short ID for farmers
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/verify/<block_hash>')
def verify_herb(block_hash):
    try:
        # Find block in blockchain
        for block in herb_blockchain.chain:
            if block.hash == block_hash:
                return jsonify({
                    'verified': True,
                    'herb_data': block.data,
                    'block_index': block.index,
                    'timestamp': block.timestamp,
                    'is_authentic': herb_blockchain.is_chain_valid()
                })

        return jsonify({'verified': False, 'message': 'Block not found'})

    except Exception as e:
        return jsonify({'verified': False, 'error': str(e)})

@app.route('/api/blockchain_status')
def blockchain_status():
    return jsonify({
        'total_blocks': len(herb_blockchain.chain),
        'is_valid': herb_blockchain.is_chain_valid(),
        'latest_hash': herb_blockchain.get_latest_block().hash
    })

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
