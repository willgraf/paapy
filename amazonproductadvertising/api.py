#!/usr/bin/env
# -*- coding: utf-8 -*-

"""Classes to wrap the Product Advertising API"""

import logging, pdb, json

from amazonproductadvertising.productadvertising import ProductAdvertisingAPI
from amazonproductadvertising.exceptions import CartException

LOGGER = logging.getLogger(__name__)


class Amazon(ProductAdvertisingAPI):

    """
    ProductAdvertisingAPI Wrapper.  Primary Interface for the API.
    Makes API requests and filters the response into a human readable,
    and developer friendly, format.
    """

    def __init__(self, AssociateTag, AWSAccessKeyId, AWSAccessKeySecret, **kwargs):
        super(Amazon, self).__init__(AssociateTag, AWSAccessKeyId, AWSAccessKeySecret, **kwargs)
        # self.cart = AmazonCart(AssociateTag, AWSAccessKeyId, AWSAccessKeySecret)
        self.item_lookup_max = 10

    def lookup(self, ItemId, **kwargs):
        """
        lookup a list of items from ItemId, if trying to lookup multiple
        ItemId, lookup will execute requests in batches of 10.
        """
        if isinstance(ItemId, str):
            ItemId = ItemId.split(',') if ',' in ItemId else ItemId
        ItemId = ItemId if isinstance(ItemId, list) else [ItemId]

        resp_group = kwargs.pop('ResponseGroup', 'ItemAttributes,OfferFull,Offers,Images,Large')

        items = []
        for i in xrange(0, len(ItemId), self.item_lookup_max):
            response = self.ItemLookup(ItemId=','.join(ItemId[i : i + self.item_lookup_max]),
                                       ResponseGroup=resp_group, **kwargs)
            try:
                xml = response['Items']['Item']
            except KeyError:
                xml = []
            xml = [xml] if not isinstance(xml, list) else xml
            items.extend(xml)

        return items


class AmazonCart(ProductAdvertisingAPI):

    """
    Amazon Cart.
    Class to perform the Amazon Cart calls.  Each class represents an Amazon Cart
    with a unique CartId and can be filled with items of type ASIN or OfferListingId.
    Each of its Items has a unique CartItemId as well.
    """

    def __init__(self, AssociateTag, AWSAccessKeyId, AWSAccessKeySecret, **kwargs):
        super(AmazonCart, self).__init__(AssociateTag, AWSAccessKeyId, AWSAccessKeySecret, **kwargs)
        item_id = kwargs.get('ItemId', kwargs.get('ASIN'))
        quantity = kwargs.get('Quantity', '1')
        self.cart_id = kwargs.get('CartId')
        self.hmac = kwargs.get('HMAC')
        self.url = kwargs.get('URL')
        self.items = kwargs.get('CartItems', [])
        self.subtotal = kwargs.get('SubTotal', 0.0)
        if not self.cart_id and item_id:
            self.create(ItemId=item_id, Quantity=quantity)

    def create(self, **kwargs):
        """returns new AmazonCart"""
        item_id = kwargs.get('ItemId', kwargs.get('ASIN'))
        quantity = kwargs.get('Quantity', '1')
        response = super(AmazonCart, self).CartCreate(ItemId=item_id, Quantity=quantity)
        self.cart_id = response['Cart'].get('CartId')
        self.hmac = response['Cart'].get('HMAC')
        self.url = response['Cart'].get('PurchaseURL')
        items = response['Cart'].get('CartItems', {}).get('CartItem', [])
        items = items if not isinstance(items, list) else [items]
        self.subtotal = int(response['Cart'].get('SubTotal', {}).get('Amount')) / 100.0
        self.items = items
        return response

    def clear(self, **kwargs):
        response = super(AmazonCart, self).CartClear(CartId=self.cart_id, HMAC=self.hmac, **kwargs)
        print(json.dumps(response))
        return response

    @staticmethod
    def get(self, CartId, CartItemId, HMAC, **kwargs):
        """
        Fetch a remote AmazonCart.  AmazonCarts will stay alive
        for ~30 days after being abandoned.
        Perhaps can save this as a field in the db for easier fulfillment.
        """
        response = super(AmazonCart, self).CartGet(CartId=CartId, HMAC=HMAC,
                                                   CartItemId=CartItemId, **kwargs)

        cart_id = response['Cart'].get('CartId')
        hmac = response['Cart'].get('URLEncodedHMAC')
        url = response['Cart'].get('PurchaseURL')
        items = response['Cart'].get('CartItems', {}).get('CartItem', [])
        items = items if not isinstance(items, list) else [items]
        self.subtotal = int(response['Cart'].get('SubTotal', {}).get('Amount')) / 100.0
        self.items = items
        return AmazonCart(CartId=CartId, CartItemId=CartItemId, HMAC=HMAC)
        pass

    def modify(self, ItemId, Quantity='0', **kwargs):
        """
        CartModify can change the Quantity of items existing in the cart,
        or move items to "SaveForLater".  Cannot add new items to the cart.
        """
        pass


    def add(self, ItemId=None, Quantity='1', **kwargs):
        """
        adds item to cart
        ItemId may be a list of ASINs (or OfferListingType, if specified as ItemIdType)
        or it may be a string of ASINs joined by commas (,).
        Quantity must either be a similar list, or if Quantity is a single value,
        that value will be applied to all items.
        """
        asin = kwargs.get('ASIN')
        if ItemId is None and asin is None:
            raise ValueError('Include your ASIN/OfferListingId in '
                             'kwargs as either ItemId or ASIN')
        if not ItemId:
            ItemId = asin

        response = super(AmazonCart, self).CartAdd(ASIN=ItemId, Quantity=Quantity,
                                                   HMAC=self.hmac, CartId=self.cart_id,
                                                   **kwargs)
        print(json.dumps(response))
        return response
        # item = {'ItemId': ItemId, 'Quantity': Quantity}
        # item.update(kwargs)
        # self.items.append(item)
