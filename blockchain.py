import json
import hashlib
from time import time
from urllib.parse import urlparse
import requests
from block import Block


class Blockchain(object):
    def __init__(self):
        self.chain = [Block(0, time(), [], "0", hashlib.sha256(str(time()).encode()).hexdigest())]
        self.current_transactions = []
        self.nodes = set()

    def new_block(self, proof, previous_hash=None):
        """
        Create a new Bock in the Blockchain
        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: (optional) Hash of the previous Block
        :return: New Block
        """

        block = Block(
            len(self.chain) + 1,
            time(),
            self.current_transactions,
            proof,
            previous_hash or self.hash(self.chain[-1])
        )

        self.current_transactions = []
        self.chain.append(block)
        return block

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of a latest block
          in the chain match.
        """
        previous_hash = self.hash(self.last_block)

        if previous_hash != block.previous_hash:
            return False

        previous_proof = self.last_block.proof
        if not self.valid_proof(previous_proof, proof):
            return False

        self.chain.append(block)
        return True

    def new_transaction(self, sender, recipient, amount):
        """
        Create a new transaction to go into the next mined block
        :param sender: Address of the sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the block that will hold this transaction
        """

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        return self.last_block.index+ 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        :return: hash
        """

        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):
        """
        Simple proof of work algorithm
            - find p' where as (pp') starts with 4 leading zeroes, where p is the previous p'
        :param last_proof: last proof
        :return: new proof
        """

        proof = 0
        while not self.valid_proof(last_proof, proof):
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the proof
            - hash(last_proof, proof) starts with 4 0's
        :param last_proof: Previous proof
        :param proof: Current proof
        :return: True if correct, else False
        """

        leading = 5
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:leading] == "0" * leading

    def register_node(self, address):
        """
        Add a node to the list of nodes
        :param address: Address of the node (url)
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, else False
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            if block.previous_hash != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block.proof, block.proof):
                return False

            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False

    def announce_new_block(self, block):
        """
        A function to announce to the network once a block has been mined.
        Other blocks can simply verify the proof of work and add it to their
        respective chains.
        :param block: Block to be added
        :return:
        """
        neighbours = self.nodes
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        for node in neighbours:
            url = f'http://{node}/add_block'
            requests.post(url, data=json.dumps(block, sort_keys=True), headers=headers)
