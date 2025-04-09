import sqlite3
from typing import List, Dict, Any, Optional

class CoffeeRepository:
    def __init__(self, db_path: str = "coffee_shop.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def _connect(self):
        """Establish a connection to the database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row 
        self.cursor = self.conn.cursor()

    def _disconnect(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def initialize(self):
        """Initialize the database schema."""
        try:
            self._connect()
            
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS coffees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                picture_url TEXT,
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                coffee_id INTEGER NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (coffee_id) REFERENCES coffees (id) ON DELETE CASCADE
            )
            ''')
            
            self.conn.commit()
            print("Database initialized successfully.")
            return True
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            return False
        finally:
            self._disconnect()

    def add_coffee(self, name: str, description: str, picture_url: str, price: float) -> int:
        """
        Add a new coffee to the database.
        
        Args:
            name: The name of the coffee
            description: Description of the coffee
            picture_url: URL to the coffee image
            price: Price of the coffee
            
        Returns:
            The ID of the newly added coffee or -1 if an error occurred
        """
        try:
            self._connect()
            self.cursor.execute('''
            INSERT INTO coffees (name, description, picture_url, price)
            VALUES (?, ?, ?, ?)
            ''', (name, description, picture_url, price))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding coffee: {e}")
            return -1
        finally:
            self._disconnect()

    def update_coffee(self, id: int, name: str, description: str, picture_url: str, price: float) -> bool:
        """
        Update an existing coffee in the database.
        
        Args:
            id: The ID of the coffee to update
            name: The updated name
            description: The updated description
            picture_url: The updated picture URL
            price: The updated price
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._connect()
            self.cursor.execute('''
            UPDATE coffees 
            SET name = ?, description = ?, picture_url = ?, price = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (name, description, picture_url, price, id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating coffee: {e}")
            return False
        finally:
            self._disconnect()

    def delete_coffee(self, id: int) -> bool:
        """
        Delete a coffee from the database.
        
        Args:
            id: The ID of the coffee to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._connect()
            self.cursor.execute('DELETE FROM coffees WHERE id = ?', (id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting coffee: {e}")
            return False
        finally:
            self._disconnect()


    def list_coffee(self, coffee_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all coffees or a specific coffee from the database.
        
        Args:
            coffee_id: Optional ID of a specific coffee to retrieve
            
        Returns:
            A list of dictionaries containing coffee details
        """
        try:
            self._connect()
            if coffee_id is not None:
                self.cursor.execute('''
                SELECT id, name, description, picture_url, price, created_at, updated_at
                FROM coffees 
                WHERE id = ?
                ''', (coffee_id,))
            else:
                self.cursor.execute('''
                SELECT id, name, description, picture_url, price, created_at, updated_at
                FROM coffees 
                ORDER BY name
                ''')
            
            result = []
            for row in self.cursor.fetchall():
                coffee = {key: row[key] for key in row.keys()}
                result.append(coffee)
                
            return result
        except sqlite3.Error as e:
            print(f"Error listing coffee: {e}")
            return []
        finally:
            self._disconnect()


    def add_to_cart(self, user_id: int, coffee_id: int, count: int = 1) -> bool:
        """
        Add a coffee to the user's cart.
        
        Args:
            user_id: The ID of the user
            coffee_id: The ID of the coffee to add
            count: The quantity to add (default: 1)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._connect()
            
            self.cursor.execute('SELECT id FROM coffees WHERE id = ?', (coffee_id,))
            if not self.cursor.fetchone():
                print(f"Coffee with ID {coffee_id} does not exist")
                return False
            
            self.cursor.execute('''
            SELECT id, count FROM cart_items 
            WHERE user_id = ? AND coffee_id = ?
            ''', (user_id, coffee_id))
            
            existing_item = self.cursor.fetchone()
            
            if existing_item:
                new_count = existing_item['count'] + count
                self.cursor.execute('''
                UPDATE cart_items SET count = ? WHERE id = ?
                ''', (new_count, existing_item['id']))
            else:
                self.cursor.execute('''
                INSERT INTO cart_items (user_id, coffee_id, count)
                VALUES (?, ?, ?)
                ''', (user_id, coffee_id, count))
                
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding to cart: {e}")
            return False
        finally:
            self._disconnect()

    def clear_cart(self, user_id: Optional[int] = None) -> bool:
        """
        Clear the cart for a specific user or all users.
        
        Args:
            user_id: The ID of the user whose cart to clear (if None, clear all carts)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._connect()
            if user_id is not None:
                self.cursor.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
            else:
                self.cursor.execute('DELETE FROM cart_items')
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error clearing cart: {e}")
            return False
        finally:
            self._disconnect()

    def get_cart_items(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all items in a user's cart with coffee details.
        
        Args:
            user_id: The ID of the user whose cart to retrieve (if None, get all cart items)
            
        Returns:
            A list of dictionaries containing cart item details
        """
        try:
            self._connect()
            if user_id is not None:
                self.cursor.execute('''
                SELECT c.id as coffee_id, c.name, c.description, c.picture_url, c.price, 
                       ci.count, (c.price * ci.count) as total_price
                FROM cart_items ci
                JOIN coffees c ON ci.coffee_id = c.id
                WHERE ci.user_id = ?
                ''', (user_id,))
            else:
                self.cursor.execute('''
                SELECT ci.user_id, c.id as coffee_id, c.name, c.description, c.picture_url, c.price, 
                       ci.count, (c.price * ci.count) as total_price
                FROM cart_items ci
                JOIN coffees c ON ci.coffee_id = c.id
                ''')
            
            result = []
            for row in self.cursor.fetchall():
                item = {key: row[key] for key in row.keys()}
                result.append(item)
                
            return result
        except sqlite3.Error as e:
            print(f"Error getting cart items: {e}")
            return []
        finally:
            self._disconnect()