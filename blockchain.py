import json
import time
import sys
import requests
import hashlib
from flask import Flask , request , jsonify
from urllib.parse import urlparse
from uuid import uuid4

class Blockchain() :
    def __init__(self ):
        self.chain = []
        self.current_trxs = []
        self.nodes = set()

        #creating Genesis block
        self.new_block(proof=100 , previous_hash=1)
    
    def new_block(self , proof , previous_hash = None):
        #creat a new block
        block = {
            'index': len(self.chain) + 1 ,
            'timestamp': time.time(),
            'transactions': self.current_trxs ,
            'previous_hash':  previous_hash or self.hash(self.chain[-1]),
            'proof': proof,
        }
        self.current_trxs = []
        self.chain.append(block)
        return block

    def new_trx(self,sender,recipient,amount):
        #add a new transaction to mempool
        self.current_trxs.append({"sender": sender , "recipient":recipient , "amount":amount})
        return self.last_block['index'] + 1
        

    def node_register(self , address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)


    def valid_chain(self , chain):
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            if block['previous_hash'] != self.hash(last_block): 
                return False
            if not self.proof_is_valid(last_block['proof'] , block['proof']):
                return False
            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)
        for node in neighbours :
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200 :
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain) :
                    max_length = length
                    new_chain = chain
                    
        if new_chain:
            self.chain = new_chain
            return True
        return False
                
                
    
    

    @staticmethod
    def hash(block):
        #hash a block
        block_string = json.dumps(block , sort_keys=True).encode()  
        return hashlib.sha256(block_string).hexdigest()
        

    @property
    def last_block(self):
        #returns the last block in the chain
        return self.chain[-1]
    
    @staticmethod
    def proof_is_valid(last_proof , proof):
        #checks if the proof is valid
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
    

    def proof_of_work(self,last_proof):
        #find a proof that satisfies the condition
        proof = 0 
        while self.proof_is_valid(last_proof , proof) is False:
            proof += 1
        return proof
    
app = Flask(__name__)
app_id = str(uuid4())
blockcahin = Blockchain()

@app.route('/mine')
def mine():
    #mine a new block
    last_block = blockcahin.last_block
    last_proof = last_block['proof']
    proof = blockcahin.proof_of_work(last_proof)
    blockcahin.new_trx(sender="0" , recipient=app_id , amount=50)
    previous_hash = blockcahin.hash(last_block)
    block = blockcahin.new_block(proof , previous_hash)

    res ={
        'massage':'new block created' ,
        'index':block['index'],
        'transactions':block['transactions'],
        'proof':block['proof'],
        'previous_hash':block['previous_hash']
    }
    return jsonify(res) , 200


@app.route('/trxs/new' , methods=['POST'])
def new_trx():
    #create a new transaction
    values = request.get_json()
    this_block = blockcahin.new_trx(values['sender'] , values['recipient'] , values['amount'])
    response = {'message': f'Trx will be added to Block {this_block}'}
    return jsonify(response) , 201


@app.route('/chain')
def full_chain():
    response = {
        'chain': blockcahin.chain,
        'length': len(blockcahin.chain),
        }
    return jsonify(response), 200

@app.route('/nodes/register' , methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')

    for node in nodes:
        blockcahin.node_register(node)
    
    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockcahin.nodes),
        }
    return jsonify(response), 201

@app.route('/nodes/resolve')
def consensus():
    replaced = blockcahin.resolve_conflicts()
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockcahin.chain
            }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockcahin.chain
            }
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0' , port=sys.argv[1])


