from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import HumanMessage

import sqlite3
import os
import json
from typing import Optional
import base64

DB_PATH = os.path.join(os.getcwd(), "store.db")

llm = ChatGoogleGenerativeAI(model="gemma-4-31b-it", temperature=0)
vision_llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0)

@tool
def get_product_rating(product_id: int) -> str:
    """retrun average rating and count of pro
    duct reviews for the given product id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("Select AVG(rating), count(*) from reviews where product_id = ?",(product_id,),)
    row = cursor.fetchone()
    conn.close()

    avg_rating = round(row[0], 2) if row[0] else 0.0
    review_count = row[1] if row[1] else 0
    res = {"product_id" : product_id, "average_rating" : avg_rating, "review_count" : review_count}

    return json.dumps(res)

@tool
def search_products(query: str, max_price: Optional[float], is_organic: Optional[bool]) -> str:
    """Search the product in database by keyword matching with name, category and description
    consider optional filters of max_price and is_organic if given

    return the json array for each matching products":
    {
    - id (int)
    - name (string)
    - category (string)
    - price (float)
    - description (string)
    - is_organic (boolean)
    }
    """

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql = "select id, name, category, price, description, is_organic from products where 1=1"
    params = []

    if query:
        sql+= " AND (name LIKE ? OR category LIKE ? OR description LIKE ?)"
        like = f"{query}"
        params.extend([like, like, like])

    if max_price is not None:
        sql+=" AND price <= ?"
        params.append(max_price)

    if is_organic is not None:
        sql+=" AND is_organic = ?"
        params.append(1 if is_organic else 0)

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    matched_products = [
        {
        "id" : row[0],
        "name" : row[1],
        "category" : row[2],
        "price" : row[3],
        "description" : row[4],
        "is_organic" : row[5]
        }
        for row in rows
    ]

    return json.dumps(matched_products)

@tool
def checkout(product_id : int) -> str:
    """Get the product information for the product_id and add that information into orders table"
    and return confirmation message with order_id, product_name, price"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("Select name, price from products where id = ?", (product_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return f"Error: Product with ProductID {product_id} not found"

    name, price = row

    cursor.execute("insert into orders(product_id, product_name, price) values(?,?,?)", (product_id, name, price,),)
    order_id = cursor.lastrowid
    # print(f"order_id: {order_id}")
    conn.commit()
    conn.close()

    return (f"congratulations! order with {order_id} has been confirmed. {name} has been placed for ${price:.2f}"
            f"Your order will arrive in 3-5 business days. Thankyou for shoppnih with us")

@tool
def describe_product_image(image_path: str) -> str:
    """Analyse the product image and return the key attributes of the product as a JSON object.
    Use this when user uploads photo of a product  they are interested in.
    the return attributes can be directly used by the search_products tool to find similar product in the store.
    """
    with open(image_path, "rb") as f: 
        image_path = base64.b64encode(f.read()).decode('utf-8')

    extension = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime_type = f"image/jpeg" if extension in ("jpg", "jpeg") else f"image/{extension}"

    message = HumanMessage(content=[{
        "type": "image_url",
        "image_url": f"data:{mime_type};base64,{image_path}",
        "caption": "Product image uploaded by user"
    },
    {
        "type": "text",
        "text": (
                "Look at this product image and extract its key attributes. "
                "Return ONLY a JSON object with these fields:\n"
                "- product_type: what kind of product it is (e.g. honey, olive oil, almonds)\n"
                "- search_query: a short keyword to search for it (e.g. 'honey', 'olive oil')\n"
                "- is_organic: true if the label says organic, false if not, null if unclear\n"
                "- description: one sentence describing the product"
        ),
    }
    ])

    result = vision_llm.invoke([message])
    return result.text

def order_history() -> str:
    """Return the json array of all the previous orders, each with:"
    - id (int)
    - product_id (int)
    - product_name (int)
    - price (int)
    - ordered_at (string, ISO format)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("Select id, product_id, product_name, price, ordered_at FROM orders order by ordered_at DESC")
    rows = cursor.fetchall()
    conn.close()

    orders = [{
                "id": row[0],
                "product_id": row[1],
                "product_name": row[2],
                "price": row[3],
                "ordered_at": row[4],
            }
        for row in rows
    ]
    return json.dumps(orders)    

def input_gaurdrail(question: str):
    """Check if question is valid for shopping agent or not
    if not return false else return true"""
    shopping_keywords = ["buy", "price", "discount", "deal", "organic", "cart", "checkout",
            "shop", "purchase", "order", "filter", "product", "yes", "rating"]

    for keyword in shopping_keywords:
        if keyword in question.lower():
            return True

    print(f"Invalid question: {question} is not related to shopping")
    print("This assistant is focused on shopping. Could you rephrase your request in terms of products or purchases?")
    return False

if __name__ == "__main__":
    SYSTEM_PROMPT = """You are a shopping assistant.

    Follow these rules:

    1. PRODUCT SEARCH
    - For any new request to find, search, show, or filter products, ALWAYS call search_products FIRST.
    - Extract query, max_price, and is_organic from the user's request.
    - Do NOT call get_product_rating or checkout before search_products.

    2. PRODUCT RESULTS
    - After search_products returns products, call get_product_rating for each returned product.
    - Show the products as a numbered list with product details, rating, and review count.

    3. ORDERING
    - Only call checkout when the user explicitly wants to buy/order a product.
    - The product_id must come from a product previously returned by search_products.
    - If multiple products were shown, use the user's selected index.
    - If only one product was shown, a confirmation such as "yes" is sufficient to proceed.

    4. IMPORTANT
    - Never invent a product_id.
    - Never use get_product_rating as the first tool for a new product search.
    - Never use checkout before a product has been found through search_products.
    - If no products match, clearly inform the user.
    """

    config = {"configurable":{"thread_id": "str(uuid.uuid4())"}}

    agent = create_agent(llm,
                tools=[search_products, get_product_rating, checkout, describe_product_image, order_history],
                system_prompt=SYSTEM_PROMPT,
                checkpointer=InMemorySaver())

    # 1. Run agent
    while True:
        type = input("You want to search(by text/image) or order or quit:")
        if not type or type in {"quit", "exit", "q"}:
            print("Goodbye! either you quitted or did not select the type of request")
            break
        else:
            question = input("What do you want to search/order:")
            if not question:
                print("Goodbye! You did not enter the question")
                break
            if type == "text" or type == "order":
                res = agent.invoke({"messages": [{"role" : "user", "content" : question}]},
                        config)
            elif type == "image":
                image_path =  os.path.join(os.getcwd(),"resources", question)
                print(f"image_path: {image_path}")
                res = agent.invoke({"messages": [{"role" : "user", "content" : {image_path}}]}, config)
            print(res["messages"][-1].text)