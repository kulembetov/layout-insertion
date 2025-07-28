#!/usr/bin/env python3
"""
User Account Creation Script
Creates user accounts for the presentation application based on Prisma schema.
Includes support for creating subscriptions with payments and symbol purchases.
"""

import os
import sys
import uuid
import hashlib
import secrets
import getpass
import configparser
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import sql
except ImportError:
    print("psycopg2 not found. Install it with: pip install psycopg2-binary")
    sys.exit(1)


class Role(Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    MIIN = "MIIN"
    SBERMARKETING = "SBERMARKETING"
    GAZPROM = "GAZPROM"
    EFES = "EFES"
    RAIFFEISEN = "RAIFFEISEN"


class Provider(Enum):
    LOCAL = "local"
    GOOGLE = "google"
    YANDEX = "yandex"
    VKONTAKTE = "vkontakte"
    TELEGRAM = "telegram"


class PaymentStatus(Enum):
    CREATED = "created"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class SubscriptionType(Enum):
    YEAR = "year"
    MONTH = "month"
    QUARTER = "quarter"


class ExecutionMode(Enum):
    AUTO = "auto"
    MANUAL = "manual"


class DatabaseManager:
    def __init__(self, mode: ExecutionMode = ExecutionMode.AUTO, config_file: str = "../database.ini"):
        self.mode = mode
        self.config_file = config_file
        self.connection = None
        
    def read_db_config(self) -> Dict[str, str]:
        """Read database configuration from ini file."""
        if not os.path.exists(self.config_file):
            print(f"Database configuration file '{self.config_file}' not found.")
            sys.exit(1)
            
        config = configparser.ConfigParser()
        config.read(self.config_file)
        
        if 'postgresql' not in config:
            print("PostgreSQL section not found in database.ini")
            sys.exit(1)
            
        db_config = dict(config['postgresql'])
        
        # Validate required fields
        required_fields = ['host', 'database', 'user', 'password', 'port']
        for field in required_fields:
            if field not in db_config or not db_config[field]:
                print(f"Missing or empty '{field}' in database.ini")
                sys.exit(1)
                
        return db_config
        
    def connect(self):
        """Establish database connection."""
        try:
            db_config = self.read_db_config()
            self.connection = psycopg2.connect(
                host=db_config['host'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password'],
                port=db_config['port']
            )
            self.connection.autocommit = False
            print("Database connected")
        except psycopg2.Error as e:
            print(f"Database connection failed: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading database configuration: {e}")
            sys.exit(1)
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            print("Database disconnected")
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Execute a database query."""
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if cursor.description:
                return cursor.fetchone()
            return None
    
    def execute_query_all(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a database query and return all results."""
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if cursor.description:
                return cursor.fetchall()
            return []
    
    def format_sql_statement(self, query: str, params: tuple = None) -> str:
        """Format SQL statement with parameters for manual mode."""
        if params is None:
            return query.strip()
        
        # Simple parameter substitution for display purposes
        formatted_query = query.strip()
        
        for param in params:
            if param is None:
                formatted_query = formatted_query.replace('%s', 'NULL', 1)
            elif isinstance(param, str):
                # Escape single quotes and wrap in quotes
                escaped_param = param.replace("'", "''")
                formatted_query = formatted_query.replace('%s', f"'{escaped_param}'", 1)
            elif isinstance(param, datetime):
                formatted_query = formatted_query.replace('%s', f"'{param.isoformat()}'", 1)
            elif isinstance(param, bool):
                formatted_query = formatted_query.replace('%s', str(param).lower(), 1)
            else:
                formatted_query = formatted_query.replace('%s', str(param), 1)
        
        return formatted_query


class PasswordHasher:
    @staticmethod
    def generate_salt() -> str:
        """Generate a random salt."""
        return secrets.token_hex(32)
    
    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        """Hash password with salt using SHA-256."""
        return hashlib.sha256((password + salt).encode()).hexdigest()


class UserAccountCreator:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.hasher = PasswordHasher()
        self.sql_statements = []  # Store generated SQL statements for manual mode
    
    def generate_uuid7(self) -> str:
        """Generate UUID7-like string (using UUID4 for simplicity)."""
        return str(uuid.uuid4())
    
    def add_sql_statement(self, description: str, query: str, params: tuple = None):
        """Add SQL statement to the list (for manual mode)."""
        formatted_sql = self.db.format_sql_statement(query, params)
        self.sql_statements.append({
            'description': description,
            'sql': formatted_sql
        })
    
    def print_sql_statements(self):
        """Print all generated SQL statements."""
        print("\n=== Generated SQL Statements ===")
        for i, stmt in enumerate(self.sql_statements, 1):
            print(f"\n-- {i}. {stmt['description']}")
            print(stmt['sql'])
        print("\n=== End SQL Statements ===")
    
    def clear_sql_statements(self):
        """Clear the SQL statements list."""
        self.sql_statements = []
    
    def get_user_input(self) -> Dict[str, Any]:
        """Collect user information through interactive input."""
        print("\n=== User Account Creation ===")
        
        user_data = {}
        
        # Username
        username = input("Username (optional): ").strip()
        user_data['username'] = username if username else None
        
        # Role selection
        print("\nAvailable roles:")
        for i, role in enumerate(Role, 1):
            print(f"{i}. {role.value}")
        
        while True:
            try:
                role_choice = input(f"Select role (1-{len(Role)}, default: USER): ").strip()
                if not role_choice:
                    user_data['role'] = Role.USER.value
                    break
                else:
                    role_index = int(role_choice) - 1
                    if 0 <= role_index < len(Role):
                        user_data['role'] = list(Role)[role_index].value
                        break
                    else:
                        print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Authentication method
        print("\nAuthentication method:")
        for i, provider in enumerate(Provider, 1):
            print(f"{i}. {provider.value}")
        
        while True:
            try:
                auth_choice = input(f"Select method (1-{len(Provider)}, default: local): ").strip()
                if not auth_choice:
                    user_data['provider'] = Provider.LOCAL.value
                    break
                else:
                    provider_index = int(auth_choice) - 1
                    if 0 <= provider_index < len(Provider):
                        user_data['provider'] = list(Provider)[provider_index].value
                        break
                    else:
                        print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Password (only for local authentication)
        if user_data['provider'] == Provider.LOCAL.value:
            while True:
                password = getpass.getpass("Password: ")
                if len(password) < 6:
                    print("Password must be at least 6 characters long.")
                    continue
                
                confirm_password = getpass.getpass("Confirm password: ")
                if password != confirm_password:
                    print("Passwords don't match. Please try again.")
                    continue
                
                user_data['password'] = password
                break
        else:
            # Auth key for non-local providers
            auth_key = input(f"{user_data['provider'].title()} identifier: ").strip()
            if not auth_key:
                print("Authentication key is required for non-local providers.")
                return self.get_user_input()
            user_data['auth_key'] = auth_key
        
        # Optional fields
        image_url = input("Profile image URL (optional): ").strip()
        user_data['image'] = image_url if image_url else None
        
        ip_address = input("IP address (optional): ").strip()
        user_data['ip'] = ip_address if ip_address else None
        
        return user_data
    
    def create_user_account(self, user_data: Dict[str, Any]) -> str:
        """Create a complete user account with all necessary records."""
        user_id = self.generate_uuid7()
        auth_id = self.generate_uuid7()
        
        if self.db.mode == ExecutionMode.MANUAL:
            print("Generating SQL statements...")
        else:
            print("Creating user account...")
        
        try:
            if self.db.mode == ExecutionMode.AUTO:
                # Auto mode: Execute SQL statements
                with self.db.connection.cursor() as cursor:
                    # 1. Create User record
                    user_query = """INSERT INTO "User" (id, role, username, image, ip, "createdAt", "presentationsCount")
VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(user_query, (
                        user_id,
                        user_data['role'],
                        user_data['username'],
                        user_data['image'],
                        user_data['ip'],
                        datetime.now(),
                        0
                    ))
                    
                    # 2. Create Auth record
                    auth_query = """INSERT INTO "Auth" (id, provider, key, "userId")
VALUES (%s, %s, %s, %s)"""
                    auth_key = user_data.get('auth_key', user_data.get('username', user_id))
                    cursor.execute(auth_query, (
                        auth_id,
                        user_data['provider'],
                        auth_key,
                        user_id
                    ))
                    
                    # 3. Create Password record (only for local auth)
                    if user_data['provider'] == Provider.LOCAL.value and 'password' in user_data:
                        salt = self.hasher.generate_salt()
                        hashed_password = self.hasher.hash_password(user_data['password'], salt)
                        
                        password_query = """INSERT INTO "Password" ("userId", password, salt)
VALUES (%s, %s, %s)"""
                        cursor.execute(password_query, (user_id, hashed_password, salt))
                    
                    # 4. Create Balance record
                    balance_query = """INSERT INTO "Balance" ("userId", symbols, "subscriptionSymbols")
VALUES (%s, %s, %s)"""
                    cursor.execute(balance_query, (user_id, 0, 0))
                    
                # Commit transaction
                self.db.connection.commit()
                
            else:
                # Manual mode: Generate SQL statements
                # 1. User record
                user_query = """INSERT INTO "User" (id, role, username, image, ip, "createdAt", "presentationsCount")
VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                self.add_sql_statement("Create User record", user_query, (
                    user_id,
                    user_data['role'],
                    user_data['username'],
                    user_data['image'],
                    user_data['ip'],
                    datetime.now(),
                    0
                ))
                
                # 2. Auth record
                auth_query = """INSERT INTO "Auth" (id, provider, key, "userId")
VALUES (%s, %s, %s, %s)"""
                auth_key = user_data.get('auth_key', user_data.get('username', user_id))
                self.add_sql_statement("Create Auth record", auth_query, (
                    auth_id,
                    user_data['provider'],
                    auth_key,
                    user_id
                ))
                
                # 3. Password record (only for local auth)
                if user_data['provider'] == Provider.LOCAL.value and 'password' in user_data:
                    salt = self.hasher.generate_salt()
                    hashed_password = self.hasher.hash_password(user_data['password'], salt)
                    
                    password_query = """INSERT INTO "Password" ("userId", password, salt)
VALUES (%s, %s, %s)"""
                    self.add_sql_statement("Create Password record", password_query, (user_id, hashed_password, salt))
                
                # 4. Balance record
                balance_query = """INSERT INTO "Balance" ("userId", symbols, "subscriptionSymbols")
VALUES (%s, %s, %s)"""
                self.add_sql_statement("Create Balance record", balance_query, (user_id, 0, 0))
            
            if self.db.mode == ExecutionMode.AUTO:
                print("User account created successfully!")
            else:
                print("SQL statements generated!")
                
            print(f"User ID: {user_id} | Username: {user_data['username'] or 'NULL'} | Role: {user_data['role']}")
            
            return user_id
            
        except psycopg2.Error as e:
            # Rollback transaction on error (only in auto mode)
            if self.db.mode == ExecutionMode.AUTO:
                self.db.connection.rollback()
            print(f"Failed to create user account: {e}")
            raise
    
    def verify_user_exists(self, user_id: str) -> bool:
        """Verify that a user exists in the database."""
        if self.db.mode == ExecutionMode.MANUAL:
            return True  # Skip verification in manual mode
            
        query = 'SELECT id FROM "User" WHERE id = %s'
        result = self.db.execute_query(query, (user_id,))
        return result is not None
    
    def save_sql_to_file(self, filename: str = "user_account_creation.sql"):
        """Save all SQL statements to a file."""
        if not self.sql_statements:
            print("No SQL statements to save.")
            return False
            
        try:
            # Check if file exists and ask to overwrite
            file_mode = 'w'
            if os.path.exists(filename):
                overwrite = input(f"File {filename} exists. Overwrite? (y/N): ").strip().lower()
                if overwrite not in ['y', 'yes']:
                    file_mode = 'a'
            
            # Use UTF-8 encoding to handle Unicode characters
            with open(filename, file_mode, encoding='utf-8') as f:
                if file_mode == 'a':
                    f.write(f"\n-- Account creation session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                else:
                    f.write("-- User Account Creation SQL Statements\n")
                    f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("BEGIN TRANSACTION;\n\n")
                
                for i, stmt in enumerate(self.sql_statements, 1):
                    f.write(f"-- {i}. {stmt['description']}\n")
                    f.write(f"{stmt['sql']};\n\n")
                
                f.write("COMMIT;\n\n")
                
            print(f"SQL statements saved to: {filename}")
            return True
        except Exception as e:
            print(f"Error saving SQL file: {e}")
            return False
    
    def get_available_plans(self) -> List[Dict]:
        """Fetch all available plans from the database."""
        print("Fetching active plans...")
        query = '''
            SELECT id, name, symbols, price, "subscriptionType", "isReccuring", description
            FROM "Plan"
            WHERE "isActive" = TRUE
            ORDER BY price ASC
        '''
        return self.db.execute_query_all(query)
    
    def get_subscription_input(self, plans: List[Dict]) -> Optional[Dict]:
        """Get subscription information from user input."""
        print("\n=== Subscription Setup ===")
        
        # Ask if user wants to create a subscription
        create_subscription = input("Create subscription? (y/N): ").strip().lower()
        if create_subscription not in ['y', 'yes']:
            return None
        
        # Display available plans from database (works in both modes now)
        if not plans:
            print("No active plans available.")
            return None
            
        mode_text = "Manual mode" if self.db.mode == ExecutionMode.MANUAL else "Auto mode"
        print(f"\n{mode_text}: Available subscription plans:")
        print("-" * 60)
        
        for i, plan in enumerate(plans, 1):
            subscription_type = plan.get('subscriptionType', 'one-time')
            recurring_text = " (Recurring)" if plan.get('isReccuring') else ""
            print(f"{i}. {plan['name'] or 'Unnamed Plan'} - {plan['price']} ₽")
            print(f"   ID: {plan['id']}")
            print(f"   Symbols: {plan['symbols']:,} | Type: {subscription_type}{recurring_text}")
            if plan['description']:
                print(f"   Description: {plan['description']}")
            print()
        
        # Plan selection
        while True:
            try:
                plan_choice = input(f"Select plan (1-{len(plans)}): ").strip()
                plan_index = int(plan_choice) - 1
                if 0 <= plan_index < len(plans):
                    selected_plan = plans[plan_index]
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Show selected plan
        print(f"\nSelected: {selected_plan['name']} ({selected_plan['price']} ₽, {selected_plan['symbols']:,} symbols)")
        
        # Payment status
        print("\nPayment status:")
        for i, status in enumerate(PaymentStatus, 1):
            print(f"{i}. {status.value}")
        
        while True:
            try:
                status_choice = input(f"Select status (1-{len(PaymentStatus)}, default: succeeded): ").strip()
                if not status_choice:
                    payment_status = PaymentStatus.SUCCEEDED.value
                    break
                else:
                    status_index = int(status_choice) - 1
                    if 0 <= status_index < len(PaymentStatus):
                        payment_status = list(PaymentStatus)[status_index].value
                        break
                    else:
                        print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Subscription duration
        duration_months = 12  # Default to 1 year
        if selected_plan.get('subscriptionType'):
            sub_type = selected_plan['subscriptionType']
            if sub_type == SubscriptionType.MONTH.value:
                duration_months = 1
            elif sub_type == SubscriptionType.QUARTER.value:
                duration_months = 3
            elif sub_type == SubscriptionType.YEAR.value:
                duration_months = 12
        
        # Custom duration override
        print(f"\nSubscription duration:")
        custom_duration = input(f"Duration in months (default: {duration_months}): ").strip()
        if custom_duration:
            try:
                duration_months = int(custom_duration)
            except ValueError:
                print("Invalid duration, using default.")
        
        return {
            'plan': selected_plan,
            'payment_status': payment_status,
            'duration_months': duration_months
        }
    
    def create_subscription(self, user_id: str, subscription_data: Dict) -> Dict[str, str]:
        """Create a complete subscription with payment and symbols purchase."""
        plan = subscription_data['plan']
        payment_status = subscription_data['payment_status']
        duration_months = subscription_data['duration_months']
        
        # Generate IDs
        payment_id = self.generate_uuid7()
        subscription_id = self.generate_uuid7()
        symbols_purchase_id = self.generate_uuid7()
        
        # Calculate dates
        now = datetime.now()
        expired_at = now + timedelta(days=duration_months * 30)  # Approximate months to days
        
        if self.db.mode == ExecutionMode.MANUAL:
            print("Generating subscription SQL...")
        else:
            print("Creating subscription...")
        
        try:
            if self.db.mode == ExecutionMode.AUTO:
                # Auto mode: Execute SQL statements
                with self.db.connection.cursor() as cursor:
                    # 1. Create Payment record
                    payment_query = """INSERT INTO "Payment" (id, "userId", status, price, description, "createdAt")
VALUES (%s, %s, %s, %s, %s, %s)"""
                    payment_description = f"Subscription to {plan['name'] or 'Plan'}"
                    cursor.execute(payment_query, (
                        payment_id,
                        user_id,
                        payment_status,
                        plan['price'],
                        payment_description,
                        now
                    ))
                    
                    # 2. Create Subscription record
                    subscription_query = """INSERT INTO "Subscription" (id, "userId", "planId", "createdAt", "expiredAt", "activeUntil")
VALUES (%s, %s, %s, %s, %s, %s)"""
                    cursor.execute(subscription_query, (
                        subscription_id,
                        user_id,
                        plan['id'],
                        now,
                        expired_at,
                        expired_at
                    ))
                    
                    # 3. Create SymbolsPurchase record
                    symbols_purchase_query = """INSERT INTO "SymbolsPurchase" (id, "userId", symbols, price, "planId", "isActive", "createdAt", "paymentId")
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(symbols_purchase_query, (
                        symbols_purchase_id,
                        user_id,
                        plan['symbols'],
                        plan['price'],
                        plan['id'],
                        payment_status == PaymentStatus.SUCCEEDED.value,  # Only active if payment succeeded
                        now,
                        payment_id
                    ))
                    
                    # 4. Create SubscriptionPayment junction record
                    subscription_payment_query = """INSERT INTO "SubscriptionPayment" ("subscriptionId", "paymentId")
VALUES (%s, %s)"""
                    cursor.execute(subscription_payment_query, (subscription_id, payment_id))
                    
                    # 5. Update user's balance if payment succeeded
                    if payment_status == PaymentStatus.SUCCEEDED.value:
                        balance_update_query = """UPDATE "Balance"
SET "subscriptionSymbols" = "subscriptionSymbols" + %s
WHERE "userId" = %s"""
                        cursor.execute(balance_update_query, (plan['symbols'], user_id))
                
                # Commit transaction
                self.db.connection.commit()
                
            else:
                # Manual mode: Generate SQL statements
                # 1. Payment record
                payment_query = """INSERT INTO "Payment" (id, "userId", status, price, description, "createdAt")
VALUES (%s, %s, %s, %s, %s, %s)"""
                payment_description = f"Subscription to {plan['name'] or 'Plan'}"
                self.add_sql_statement("Create Payment record", payment_query, (
                    payment_id,
                    user_id,
                    payment_status,
                    plan['price'],
                    payment_description,
                    now
                ))
                
                # 2. Subscription record
                subscription_query = """INSERT INTO "Subscription" (id, "userId", "planId", "createdAt", "expiredAt", "activeUntil")
VALUES (%s, %s, %s, %s, %s, %s)"""
                self.add_sql_statement("Create Subscription record", subscription_query, (
                    subscription_id,
                    user_id,
                    plan['id'],
                    now,
                    expired_at,
                    expired_at
                ))
                
                # 3. SymbolsPurchase record
                symbols_purchase_query = """INSERT INTO "SymbolsPurchase" (id, "userId", symbols, price, "planId", "isActive", "createdAt", "paymentId")
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                self.add_sql_statement("Create SymbolsPurchase record", symbols_purchase_query, (
                    symbols_purchase_id,
                    user_id,
                    plan['symbols'],
                    plan['price'],
                    plan['id'],
                    payment_status == PaymentStatus.SUCCEEDED.value,
                    now,
                    payment_id
                ))
                
                # 4. SubscriptionPayment junction record
                subscription_payment_query = """INSERT INTO "SubscriptionPayment" ("subscriptionId", "paymentId")
VALUES (%s, %s)"""
                self.add_sql_statement("Create SubscriptionPayment junction record", subscription_payment_query, (subscription_id, payment_id))
                
                # 5. Update balance if payment succeeded
                if payment_status == PaymentStatus.SUCCEEDED.value:
                    balance_update_query = """UPDATE "Balance"
SET "subscriptionSymbols" = "subscriptionSymbols" + %s
WHERE "userId" = %s"""
                    self.add_sql_statement("Update Balance.subscriptionSymbols", balance_update_query, (plan['symbols'], user_id))
            
            if self.db.mode == ExecutionMode.AUTO:
                print("Subscription created successfully!")
            else:
                print("Subscription SQL generated!")
                
            print(f"Plan: {plan['name']} | Price: {plan['price']} ₽ | Symbols: {plan['symbols']:,} | Status: {payment_status}")
            print(f"Expires: {expired_at.strftime('%Y-%m-%d')}")
            
            return {
                'payment_id': payment_id,
                'subscription_id': subscription_id,
                'symbols_purchase_id': symbols_purchase_id
            }
            
        except psycopg2.Error as e:
            # Rollback transaction on error (only in auto mode)
            if self.db.mode == ExecutionMode.AUTO:
                self.db.connection.rollback()
            print(f"Failed to create subscription: {e}")
            raise


def select_execution_mode() -> ExecutionMode:
    """Allow user to select execution mode."""
    print("User Account Creation Script")
    print("Modes:")
    print("1. AUTO - Execute SQL in database")
    print("2. MANUAL - Generate SQL statements only")
    
    while True:
        try:
            mode_choice = input("\nSelect mode (1-2, default: AUTO): ").strip()
            if not mode_choice or mode_choice == "1":
                return ExecutionMode.AUTO
            elif mode_choice == "2":
                return ExecutionMode.MANUAL
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)


def main():
    """Main function to run the user account creation script."""
    # Select execution mode
    mode = select_execution_mode()
    
    print(f"\nMode: {mode.value.upper()}")
    
    # Initialize database manager and connect
    db_manager = DatabaseManager(mode=mode, config_file="../database.ini")
    db_manager.connect()
    
    try:
        # Initialize account creator
        creator = UserAccountCreator(db_manager)
        
        while True:
            try:
                # Clear previous SQL statements for manual mode
                if mode == ExecutionMode.MANUAL:
                    creator.clear_sql_statements()
                
                # Get user input
                user_data = creator.get_user_input()
                
                # Show summary and confirm
                print("\n=== Account Summary ===")
                print(f"Username: {user_data['username'] or 'NULL'}")
                print(f"Role: {user_data['role']}")
                print(f"Auth: {user_data['provider']}")
                if user_data['provider'] == Provider.LOCAL.value:
                    print(f"Password: [WILL BE HASHED]")
                else:
                    print(f"Auth Key: {user_data.get('auth_key', 'N/A')}")
                
                action_text = "Create account" if mode == ExecutionMode.AUTO else "Generate SQL"
                confirm = input(f"\n{action_text}? (y/N): ").strip().lower()
                
                if confirm in ['y', 'yes']:
                    user_id = creator.create_user_account(user_data)
                    
                    # Verify account creation (only in auto mode)
                    if creator.verify_user_exists(user_id):
                        if mode == ExecutionMode.AUTO:
                            print("Account verification: PASSED")
                        
                        # Get available plans and ask about subscription
                        plans = creator.get_available_plans()
                        subscription_data = creator.get_subscription_input(plans)
                        
                        if subscription_data:
                            try:
                                subscription_ids = creator.create_subscription(user_id, subscription_data)
                                if mode == ExecutionMode.AUTO:
                                    print("Subscription verification: PASSED")
                            except Exception as sub_error:
                                print(f"Subscription creation failed: {sub_error}")
                        else:
                            print("No subscription created.")
                    else:
                        print("Account verification: FAILED")
                    
                    # Print SQL statements in manual mode
                    if mode == ExecutionMode.MANUAL and creator.sql_statements:
                        creator.print_sql_statements()
                        
                        # Ask if user wants to save SQL to file
                        save_sql = input("\nSave all SQL statements to file? (y/N): ").strip().lower()
                        if save_sql in ['y', 'yes']:
                            filename = input("Enter filename (default: user_account_creation.sql): ").strip()
                            if not filename:
                                filename = "user_account_creation.sql"
                            creator.save_sql_to_file(filename)
                        
                else:
                    action_text = "Account creation" if mode == ExecutionMode.AUTO else "SQL generation"
                    print(f"{action_text} cancelled")
                
            except KeyboardInterrupt:
                print("\nCancelled")
                break
            except Exception as e:
                print(f"Error: {e}")
            
            # Ask if user wants to create another account
            another_text = "Create another account" if mode == ExecutionMode.AUTO else "Generate SQL for another account"
            another = input(f"\n{another_text}? (y/N): ").strip().lower()
            if another not in ['y', 'yes']:
                break
    
    finally:
        db_manager.disconnect()
    
    print("Complete")


if __name__ == "__main__":
    main()