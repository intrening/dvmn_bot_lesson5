import requests
import os
from pprint import pprint


EP_ACCESS_TOKEN = None


def fetch_products():
    url = 'https://api.moltin.com/v2/products'
    headers = {'Authorization': f'Bearer {get_ep_access_token()}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status() 
    return response.json()['data']


def get_image_url(id):
    url = f'https://api.moltin.com/v2/files/{id}'
    headers = {'Authorization': f'Bearer {get_ep_access_token()}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status() 
    return response.json()['data']['link']['href']


def get_project(id):
    url = f'https://api.moltin.com/v2/products/{id}'
    headers = {'Authorization': f'Bearer {get_ep_access_token()}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status() 
    return response.json()['data']


def get_ep_access_token():
    global EP_ACCESS_TOKEN
    if not EP_ACCESS_TOKEN:
        client_id = os.environ.get('EP_CLIENT_ID')
        url = 'https://api.moltin.com/oauth/access_token'
        payload = {
            'client_id': client_id,
            'grant_type': 'implicit',
        }
        response = requests.post(url, data=payload)
        response.raise_for_status()
        EP_ACCESS_TOKEN = response.json()['access_token']
    return EP_ACCESS_TOKEN


def add_to_cart(prod_id, quantity, chat_id):
    url = f'https://api.moltin.com/v2/carts/:{chat_id}/items'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'id': prod_id,
            'quantity': int(quantity),
            'type': 'cart_item',
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()


def show_cart(chat_id):
    url = f'https://api.moltin.com/v2/carts/:{chat_id}/items'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    pprint(response.json())
