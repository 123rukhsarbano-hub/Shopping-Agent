# Shopping-Agent
This is a shopping assistant which basically search the product and applies filters like is_organic and max_price based on the user query and list all the matching products present in the inventory. Further, if user want to order any of the products listed by saying index no or product it will order it and give the confirmatiion message. The ordered product will be listed into the 'orders' table with the order ID.

inputs: We have 'reviews' and 'products' in our databse and used sqlite3 to access these tables.
output: 'orders' table to list the order history.

- run using cmd: python ShoppingAssistant.py

- Eg:
python .\ShoppingAssistant.py
You want to search(by text/image) or order or quit:text
What do you want to search/order:i want to buy organic honey with 4+ rating and less than $20
I found a few organic honey options for you under $20 with a 4+ rating:

1. **Organic Raw Honey** - $14.99
   - Rating: 4.62 (4 reviews)
   - Description: Pure organic raw honey, unfiltered and cold-pressed.

2. **Organic Buckwheat Honey** - $18.99
   - Rating: 4.62 (4 reviews)
   - Description: Dark and robust organic buckwheat honey, antioxidant-rich.

3. **Organic Acacia Honey** - $17.99
   - Rating: 4.75 (4 reviews)
   - Description: Light and mild organic acacia honey, low glycemic index.

Which one would you like to buy?
You want to search(by text/image) or order or quit:order
What do you want to search/order:order #3
Your order for the **Organic Acacia Honey** has been confirmed! 

**Order ID:** 16
**Price:** $17.99
Your order will arrive in 3-5 business days. Thank you for shopping with us!
You want to search(by text/image) or order or quit:q
Goodbye! either you quitted or did not select the type of request
 
