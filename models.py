from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """نموذج المستخدمين"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin, user, viewer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """تشفير كلمة المرور"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """التحقق من كلمة المرور"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Customer(db.Model):
    """نموذج العملاء"""
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    tax_number = db.Column(db.String(50))
    credit_limit = db.Column(db.Float, default=0.0)
    current_balance = db.Column(db.Float, default=0.0)  # موجب = مدين، سالب = دائن
    currency = db.Column(db.String(10), default='SYP')  # عملة العميل الافتراضية
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    invoices = db.relationship('Invoice', backref='customer', lazy=True)
    payments = db.relationship('Payment', backref='customer', lazy=True)
    
    def __repr__(self):
        return f'<Customer {self.name}>'

class Supplier(db.Model):
    """نموذج الموردين"""
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    tax_number = db.Column(db.String(50))
    current_balance = db.Column(db.Float, default=0.0)  # موجب = دائن، سالب = مدين
    currency = db.Column(db.String(10), default='SYP')  # عملة المورد الافتراضية
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    invoices = db.relationship('Invoice', backref='supplier', lazy=True)
    payments = db.relationship('Payment', backref='supplier', lazy=True)
    
    def __repr__(self):
        return f'<Supplier {self.name}>'

class Warehouse(db.Model):
    """نموذج المخازن"""
    __tablename__ = 'warehouses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))
    manager = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    products = db.relationship('Product', backref='warehouse', lazy=True)
    inventory_movements = db.relationship('InventoryMovement', backref='warehouse', lazy=True)
    
    def __repr__(self):
        return f'<Warehouse {self.name}>'

class Product(db.Model):
    """نموذج الأصناف"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(20), default='قطعة')
    cost_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    quantity = db.Column(db.Float, default=0.0)
    min_quantity = db.Column(db.Float, default=0.0)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    category = db.Column(db.String(50))
    barcode = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    invoice_items = db.relationship('InvoiceItem', backref='product', lazy=True)
    inventory_movements = db.relationship('InventoryMovement', backref='product', lazy=True)
    
    @property
    def is_low_stock(self):
        """التحقق من نقص المخزون"""
        return self.quantity <= self.min_quantity
    
    def __repr__(self):
        return f'<Product {self.name}>'

class Invoice(db.Model):
    """نموذج الفواتير"""
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    invoice_type = db.Column(db.String(20), nullable=False)  # sale, purchase
    invoice_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    due_date = db.Column(db.Date)

    # العميل أو المورد
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))

    # المبالغ
    subtotal = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    discount_percentage = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    tax_percentage = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    remaining_amount = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='SYP')  # عملة الفاتورة

    # معلومات إضافية
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')  # draft, confirmed, paid, cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy=True)
    journal_entries = db.relationship('JournalEntry', backref='invoice', lazy=True)

    @property
    def is_paid(self):
        """التحقق من سداد الفاتورة"""
        return self.remaining_amount <= 0

    def calculate_totals(self):
        """حساب إجماليات الفاتورة"""
        self.subtotal = sum(item.total_amount for item in self.items)

        # حساب الخصم
        if self.discount_percentage > 0:
            self.discount_amount = self.subtotal * (self.discount_percentage / 100)

        # حساب الضريبة
        taxable_amount = self.subtotal - self.discount_amount
        if self.tax_percentage > 0:
            self.tax_amount = taxable_amount * (self.tax_percentage / 100)

        # المجموع النهائي
        self.total_amount = taxable_amount + self.tax_amount
        self.remaining_amount = self.total_amount - self.paid_amount

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'

class InvoiceItem(db.Model):
    """نموذج عناصر الفاتورة"""
    __tablename__ = 'invoice_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)

    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0.0)
    discount_percentage = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_total(self):
        """حساب إجمالي العنصر"""
        subtotal = self.quantity * self.unit_price

        # حساب الخصم
        if self.discount_percentage > 0:
            self.discount_amount = subtotal * (self.discount_percentage / 100)

        self.total_amount = subtotal - self.discount_amount

    def __repr__(self):
        return f'<InvoiceItem {self.product.name}>'

class Payment(db.Model):
    """نموذج الدفعات (سندات القبض والدفع)"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    payment_number = db.Column(db.String(50), unique=True, nullable=False)
    payment_type = db.Column(db.String(20), nullable=False)  # receipt, payment
    payment_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())

    # العميل أو المورد
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))

    # الفاتورة المرتبطة (اختيارية)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))

    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='SYP')  # عملة السند
    payment_method = db.Column(db.String(20), default='cash')  # cash, bank, check, card
    reference_number = db.Column(db.String(100))  # رقم الشيك أو الحوالة
    bank_name = db.Column(db.String(100))

    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    journal_entries = db.relationship('JournalEntry', backref='payment', lazy=True)

    def __repr__(self):
        return f'<Payment {self.payment_number}>'

class InventoryMovement(db.Model):
    """نموذج حركة المخزون"""
    __tablename__ = 'inventory_movements'

    id = db.Column(db.Integer, primary_key=True)
    movement_type = db.Column(db.String(20), nullable=False)  # in, out, transfer, adjustment
    movement_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())

    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)

    quantity = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float, default=0.0)
    total_cost = db.Column(db.Float, default=0.0)

    # المرجع (فاتورة، تحويل، تسوية)
    reference_type = db.Column(db.String(20))  # invoice, transfer, adjustment
    reference_id = db.Column(db.Integer)
    reference_number = db.Column(db.String(50))

    # للتحويل بين المخازن
    to_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'))

    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<InventoryMovement {self.movement_type} - {self.product.name}>'

class JournalEntry(db.Model):
    """نموذج دفتر اليومية"""
    __tablename__ = 'journal_entries'

    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    entry_type = db.Column(db.String(20), nullable=False)  # invoice, payment, adjustment

    # المرجع
    reference_type = db.Column(db.String(20))  # invoice, payment
    reference_id = db.Column(db.Integer)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'))

    description = db.Column(db.Text, nullable=False)
    debit_amount = db.Column(db.Float, default=0.0)
    credit_amount = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='SYP')  # عملة القيد

    # الحساب المدين والدائن
    debit_account = db.Column(db.String(100))
    credit_account = db.Column(db.String(100))

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<JournalEntry {self.description}>'

class CurrencySettings(db.Model):
    """نموذج إعدادات العملات المتعددة"""
    __tablename__ = 'currency_settings'

    id = db.Column(db.Integer, primary_key=True)
    currency_code = db.Column(db.String(10), nullable=False, unique=True)  # USD, EUR, etc.
    currency_name = db.Column(db.String(50), nullable=False)  # دولار أمريكي
    currency_symbol = db.Column(db.String(10), nullable=False)  # $
    exchange_rate = db.Column(db.Float, default=1.0)  # سعر الصرف مقابل العملة الأساسية
    is_base_currency = db.Column(db.Boolean, default=False)  # هل هي العملة الأساسية
    is_active = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CurrencySettings {self.currency_code}>'

class CompanySettings(db.Model):
    """نموذج إعدادات الشركة"""
    __tablename__ = 'company_settings'

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), nullable=False, unique=True)
    setting_value = db.Column(db.Text)
    setting_type = db.Column(db.String(20), default='string')  # string, boolean, number, json
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CompanySettings {self.setting_key}>'
