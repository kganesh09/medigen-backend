from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_mysqldb import MySQL
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
import dbconfig

app = Flask(__name__)
CORS(app)  

# Configure MySQL using the details from dbconfig.py
app.config['MYSQL_HOST'] = dbconfig.MYSQL_HOST
app.config['MYSQL_USER'] = dbconfig.MYSQL_USER
app.config['MYSQL_PASSWORD'] = dbconfig.MYSQL_PASSWORD
app.config['MYSQL_DB'] = dbconfig.MYSQL_DB
app.config['JWT_SECRET_KEY'] = 'mukeshraj'
# app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1) 

mysql = MySQL(app)
jwt = JWTManager(app)

DUMMY_USER = {
    "username": "admin",
    "password": "password123"
}

# Route for login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if user and user[3] == password:  # Assuming password is 4th column
        access_token = create_access_token(identity=email)

        # Assuming columns: id, name, email, password, phoneno, profilePicture
        user_data = {
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "phoneno": user[4]
        }

        return jsonify({
            "access_token": access_token,
            "user": user_data
        }), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401



@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    phoneNumber=data.get('phoneNumber')

    try:
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO users (name, email, password, phoneNumber) VALUES (%s, %s, %s, %s)', (name, email, password, phoneNumber))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'message': 'User registered successfully!'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Example route to fetch data from MySQL
@app.route('/product', methods=['GET'])
@jwt_required()
def get_products():
    try:
        # Get the current user identity from the token
        current_user = get_jwt_identity()
        print(f"Current user: {current_user}")  # Log current user to verify if the token is valid
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT p.*, s.name AS salt_name FROM products p LEFT JOIN salts s ON p.id = s.product_id;')
        products = cursor.fetchall()

        return jsonify([{
            'id': product[0],
            'productname': product[1],
            'productavgprice': product[2],
            'productprice': product[3],
            'productImageUrl': product[4],
            'productlab': product[5],
            'productsaltname': product[6]
        } for product in products])

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 422


@app.route('/description/<int:id>', methods=['GET'])  # Use a path parameter
@jwt_required()
def get_description(id):  # Accept the 'id' as a parameter
    try:
        cursor = mysql.connection.cursor()
        # Query the database for the specific product description
        cursor.execute('SELECT * FROM `descriptions` WHERE `product_id` = %s', (id,))
        description = cursor.fetchone()

        # If no description is found, return a 404 error
        if not description:
            return jsonify({'error': 'Description not found'}), 404

        # Return the description as JSON
        return jsonify({
            'id': description[1],
            'productname': description[2],
            'content': description[3],
            'uses': description[4],
            'howtouse': description[5],
            'sideeffects': description[6],
            'questions': description[7]
        })
    except Exception as e:
        # Handle any exceptions that occur
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()



@app.route('/allproduct', methods=['GET'])
@jwt_required()
def get_allproduct():
    try:
        cursor = mysql.connection.cursor()  # Regular cursor without `dictionary=True`
        
        # Query to fetch products, their chemical compositions, and reviews
        query = '''
        SELECT 
            p.id AS product_id,
            p.name AS productname,
            p.avgprice,
            p.price,
            p.image_url,
            p.labname,
            c.chemicalname,
            c.name,
            r.rating,
            r.comment
        FROM 
            products p
        LEFT JOIN 
            salts c ON p.id = c.product_id
        LEFT JOIN 
            reviews r ON p.id = r.product_id
        '''
        cursor.execute(query)
        result = cursor.fetchall()
        
        # Get column names for mapping to dictionary
        column_names = [column[0] for column in cursor.description]
        
        # Convert result to list of dictionaries
        rows = [dict(zip(column_names, row)) for row in result]
        
        # Grouping data into a structured response
        products = {}
        for row in rows:
            product_id = row["product_id"]
            if product_id not in products:
                products[product_id] = {
                    "id": row["product_id"],
                    "productname": row["productname"],
                    "avgprice": row["avgprice"],
                    "price": row["price"],
                    "image_url": row["image_url"],
                    "labname": row["labname"],
                    "chemical_names": row["chemicalname"],
                    "genericname": row["name"],
                    "reviews": []
                }
            
            
            
            # Add reviews if available
            if row["rating"] and row["comment"]:
                products[product_id]["reviews"].append({
                    "rating": row["rating"],
                    "review": row["comment"]
                })
        
        # Return the products as a list
        return jsonify(list(products.values())), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/questions/<int:id>', methods=['GET']) 
@jwt_required()
def get_question(id):  
    try:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT question,productname FROM `descriptions` WHERE `product_id` = %s', (id,))
        question = cursor.fetchone()

        if not question:
            return jsonify({'error': 'question not found'}), 404

        return jsonify({
            'questions': question[0],
            'productname': question[1]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()


@app.route('/reviews/<int:id>', methods=['GET'])
@jwt_required()
def get_reviews(id):  
    try:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT product_id, rating, comment FROM `reviews` WHERE `product_id` = %s', (id,))
        reviews = cursor.fetchall()  

        if not reviews:
            return jsonify({'error': 'No reviews found for this product'}), 404

        reviews_list = [{
            'product_id': review[0],
            'rating': review[1],
            'comment': review[2]
        } for review in reviews]

        return jsonify({'reviews': reviews_list})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()



@app.route('/add-to-cart', methods=['POST'])
@jwt_required()
def add_to_cart():
    try:
        current_user = get_jwt_identity()
        data = request.json
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        if not product_id or quantity == 0:
            return jsonify({'error': 'Invalid product or quantity'}), 400

        cursor = mysql.connection.cursor()

        # Check if product exists
        cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()
        if not product:
            return jsonify({'error': 'Product not found'}), 404

        # Check if item already in cart
        cursor.execute('SELECT * FROM cart WHERE product_id = %s AND user_email = %s', (product_id, current_user))
        cart_item = cursor.fetchone()

        if cart_item:
            new_quantity = cart_item[2] + quantity  # cart_item[2] is quantity

            if new_quantity <= 0:
                # Remove item from cart if quantity goes to 0 or below
                cursor.execute('DELETE FROM cart WHERE product_id = %s AND user_email = %s',
                               (product_id, current_user))
            else:
                # Update with new quantity
                cursor.execute('UPDATE cart SET quantity = %s WHERE product_id = %s AND user_email = %s',
                               (new_quantity, product_id, current_user))
        else:
            if quantity > 0:
                cursor.execute('INSERT INTO cart (product_id, quantity, user_email) VALUES (%s, %s, %s)',
                               (product_id, quantity, current_user))
            else:
                return jsonify({'error': 'Invalid operation: Cannot subtract from non-existent cart item'}), 400

        mysql.connection.commit()
        return jsonify({'message': 'Cart updated successfully'}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500




@app.route('/cart', methods=['GET'])
@jwt_required()
def get_cart():
    try:
        current_user = get_jwt_identity()
        cursor = mysql.connection.cursor()
        cursor.execute('''
            SELECT p.id, p.name, p.price, p.image_url, c.quantity
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_email = %s
        ''', (current_user,))
        cart_items = cursor.fetchall()

        if not cart_items:
            return jsonify({'message': 'Your cart is empty'}), 200

        cart = [{
            'product_id': item[0],
            'product_name': item[1],
            'product_price': item[2],
            'product_img': item[3],
            'quantity': item[4]
        } for item in cart_items]

        return jsonify({'cart': cart}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/remove-cart', methods=['POST'])
@jwt_required()
def remove_cart():
    try:
        current_user = get_jwt_identity()
        data = request.json
        product_id = data.get('product_id')

        if not product_id:
           return jsonify({'error': 'Invalid product'}), 400

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM cart WHERE product_id = %s AND user_email = %s', (product_id, current_user))
        cart_item = cursor.fetchone()

        if cart_item:
            cursor.execute('DELETE FROM cart WHERE product_id = %s AND user_email = %s',
                           (product_id, current_user))
            mysql.connection.commit()
            return jsonify({'message': 'Product removed from cart'}), 200
        else:
            return jsonify({'message': 'Product not in cart'}), 404

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/order', methods=['POST'])
@jwt_required()
def place_order():
    try:
        current_user = get_jwt_identity()
        cursor = mysql.connection.cursor()

        # Fetch all cart items for this user
        cursor.execute('SELECT product_id, quantity FROM cart WHERE user_email = %s', (current_user,))
        cart_items = cursor.fetchall()

        if not cart_items:
            return jsonify({'message': 'No items in cart to place order'}), 400

        # Insert into orders
        for item in cart_items:
            cursor.execute('INSERT INTO orders (user_email, product_id, quantity) VALUES (%s, %s, %s)',
                           (current_user, item[0], item[1]))

        # Clear the user's cart
        cursor.execute('DELETE FROM cart WHERE user_email = %s', (current_user,))

        mysql.connection.commit()
        return jsonify({'message': 'Order placed successfully'}), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    try:
        current_user = get_jwt_identity()
        cursor = mysql.connection.cursor()

        # Join to get product details along with order info
        cursor.execute('''
            SELECT o.id, o.product_id, o.quantity, p.name, p.price, o.order_date, p.image_url
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.user_email = %s
            ORDER BY o.order_date DESC
        ''', (current_user,))

        orders = cursor.fetchall()

        order_list = []
        for order in orders:
            order_list.append({
                'order_id': order[0],
                'product_id': order[1],
                'quantity': order[2],
                'product_name': order[3],
                'product_price': float(order[4]),
                'timestamp': order[5].strftime("%Y-%m-%d %H:%M:%S"),
                'product_img': order[6]
            })

        return jsonify({'orders': order_list}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)


