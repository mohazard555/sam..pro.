from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from config import config
from models import db, User, Customer, Supplier, Warehouse, Product, Invoice, InvoiceItem, Payment, InventoryMovement, JournalEntry, CurrencySettings, CompanySettings
from datetime import datetime, date
import os
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

def create_app(config_name=None):
    """إنشاء تطبيق Flask"""
    app = Flask(__name__)
    
    # تحديد بيئة التشغيل
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # تهيئة قاعدة البيانات
    db.init_app(app)
    
    # تهيئة التطبيق
    config[config_name].init_app(app)
    
    return app

# إنشاء التطبيق
app = create_app()

@app.before_first_request
def create_tables():
    """إنشاء جداول قاعدة البيانات"""
    db.create_all()
    
    # إنشاء مستخدم افتراضي
    if not User.query.first():
        admin_user = User(
            username='admin',
            email='admin@sampro.com',
            full_name='مدير النظام',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        
        # إنشاء مخزن افتراضي
        default_warehouse = Warehouse(
            name='المخزن الرئيسي',
            location='المقر الرئيسي',
            manager='مدير المخزن'
        )
        db.session.add(default_warehouse)

        # إنشاء العملات الافتراضية
        default_currencies = [
            {'code': 'SYP', 'name': 'ليرة سورية', 'symbol': 'ل.س', 'rate': 1.0, 'is_base': True},
            {'code': 'USD', 'name': 'دولار أمريكي', 'symbol': '$', 'rate': 15000.0, 'is_base': False},
            {'code': 'EUR', 'name': 'يورو', 'symbol': '€', 'rate': 16000.0, 'is_base': False},
            {'code': 'TRY', 'name': 'ليرة تركية', 'symbol': '₺', 'rate': 500.0, 'is_base': False},
            {'code': 'SAR', 'name': 'ريال سعودي', 'symbol': 'ر.س', 'rate': 4000.0, 'is_base': False},
            {'code': 'AED', 'name': 'درهم إماراتي', 'symbol': 'د.إ', 'rate': 4100.0, 'is_base': False},
        ]

        for curr in default_currencies:
            if not CurrencySettings.query.filter_by(currency_code=curr['code']).first():
                currency = CurrencySettings(
                    currency_code=curr['code'],
                    currency_name=curr['name'],
                    currency_symbol=curr['symbol'],
                    exchange_rate=curr['rate'],
                    is_base_currency=curr['is_base']
                )
                db.session.add(currency)

        # إنشاء إعدادات الشركة الافتراضية
        default_settings = [
            {'key': 'enable_multi_currency', 'value': 'false', 'type': 'boolean', 'desc': 'تفعيل العملات المتعددة'},
            {'key': 'base_currency', 'value': 'SYP', 'type': 'string', 'desc': 'العملة الأساسية'},
            {'key': 'company_name', 'value': 'SAM PRO', 'type': 'string', 'desc': 'اسم الشركة'},
            {'key': 'tax_rate', 'value': '0.0', 'type': 'number', 'desc': 'معدل الضريبة الافتراضي'},
        ]

        for setting in default_settings:
            if not CompanySettings.query.filter_by(setting_key=setting['key']).first():
                company_setting = CompanySettings(
                    setting_key=setting['key'],
                    setting_value=setting['value'],
                    setting_type=setting['type'],
                    description=setting['desc']
                )
                db.session.add(company_setting)

        db.session.commit()

# الصفحة الرئيسية
@app.route('/')
def index():
    """الصفحة الرئيسية - لوحة التحكم"""
    # إحصائيات سريعة
    stats = {
        'customers_count': Customer.query.filter_by(is_active=True).count(),
        'suppliers_count': Supplier.query.filter_by(is_active=True).count(),
        'products_count': Product.query.filter_by(is_active=True).count(),
        'invoices_count': Invoice.query.count(),
        'total_sales': db.session.query(db.func.sum(Invoice.total_amount)).filter(
            Invoice.invoice_type == 'sale',
            Invoice.status == 'confirmed'
        ).scalar() or 0,
        'total_purchases': db.session.query(db.func.sum(Invoice.total_amount)).filter(
            Invoice.invoice_type == 'purchase',
            Invoice.status == 'confirmed'
        ).scalar() or 0,
        'pending_payments': db.session.query(db.func.sum(Invoice.remaining_amount)).filter(
            Invoice.remaining_amount > 0
        ).scalar() or 0,
        'low_stock_products': Product.query.filter(
            Product.quantity <= Product.min_quantity,
            Product.is_active == True
        ).count()
    }
    
    # آخر الفواتير
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    # المنتجات منخفضة المخزون - نظام محسن ودقيق
    from sqlalchemy import func, case, and_, or_

    # الحصول على جميع المنتجات النشطة مع الحد الأدنى المحدد
    active_products = Product.query.filter(
        Product.is_active == True,
        Product.min_quantity > 0
    ).all()

    enhanced_low_stock = []

    for product in active_products:
        # حساب الكمية الفعلية من حركات المخزون
        movements = InventoryMovement.query.filter_by(
            product_id=product.id,
            warehouse_id=product.warehouse_id
        ).all()

        calculated_quantity = 0
        total_in = 0
        total_out = 0

        for movement in movements:
            quantity = float(movement.quantity) if movement.quantity else 0

            # معالجة شاملة لجميع أنواع الحركات
            if movement.movement_type in ['in', 'purchase', 'return_sale', 'transfer_in']:
                total_in += abs(quantity)
                calculated_quantity += abs(quantity)
            elif movement.movement_type in ['out', 'sale', 'return_purchase', 'transfer_out', 'damage']:
                total_out += abs(quantity)
                calculated_quantity -= abs(quantity)
            elif movement.movement_type == 'adjustment':
                # التسوية يمكن أن تكون موجبة أو سالبة
                if quantity >= 0:
                    total_in += quantity
                    calculated_quantity += quantity
                else:
                    total_out += abs(quantity)
                    calculated_quantity += quantity  # quantity سالب بالفعل
            elif movement.movement_type == 'transfer':
                # التحويل بين المخازن
                if movement.warehouse_id == product.warehouse_id:
                    # إخراج من المخزن الحالي
                    total_out += abs(quantity)
                    calculated_quantity -= abs(quantity)
                elif hasattr(movement, 'to_warehouse_id') and movement.to_warehouse_id == product.warehouse_id:
                    # إدخال للمخزن الحالي
                    total_in += abs(quantity)
                    calculated_quantity += abs(quantity)

        # التأكد من عدم وجود كميات سالبة
        calculated_quantity = max(0, calculated_quantity)

        # استخدام الكمية المحسوبة كمرجع أساسي
        current_quantity = calculated_quantity

        # إذا كانت الكمية المسجلة أكبر من المحسوبة، استخدم الأكبر (للأمان)
        if product.quantity and product.quantity > calculated_quantity:
            current_quantity = product.quantity

        # التحقق من نقص المخزون مع مستويات متدرجة
        is_low_stock = current_quantity <= product.min_quantity
        is_critical = current_quantity <= (product.min_quantity * 0.5)  # أقل من 50% من الحد الأدنى
        is_out_of_stock = current_quantity <= 0
        is_very_low = current_quantity <= (product.min_quantity * 0.2)  # أقل من 20% من الحد الأدنى

        if is_low_stock:
            # حساب نسبة النقص والأولوية
            shortage = max(0, product.min_quantity - current_quantity)
            shortage_percentage = round((shortage / product.min_quantity * 100), 1) if product.min_quantity > 0 else 0

            # تحديد مستوى الخطورة مع تفصيل أكثر دقة
            if is_out_of_stock:
                urgency_level = 'critical'
                urgency_text = 'نفد المخزون'
                urgency_color = 'danger'
                priority = 1
            elif is_very_low:
                urgency_level = 'critical'
                urgency_text = 'حرج جداً - أقل من 20%'
                urgency_color = 'danger'
                priority = 2
            elif is_critical:
                urgency_level = 'high'
                urgency_text = 'حرج - أقل من 50%'
                urgency_color = 'danger'
                priority = 3
            elif current_quantity <= (product.min_quantity * 0.8):
                urgency_level = 'medium'
                urgency_text = 'منخفض - أقل من 80%'
                urgency_color = 'warning'
                priority = 4
            else:
                urgency_level = 'low'
                urgency_text = 'تحذير - عند الحد الأدنى'
                urgency_color = 'info'
                priority = 5

            # حساب الكمية المطلوبة للوصول للحد الآمن
            safe_quantity = product.min_quantity * 1.5  # 150% من الحد الأدنى
            required_quantity = max(0, safe_quantity - current_quantity)

            # تقدير التكلفة المطلوبة
            estimated_cost = required_quantity * (product.cost_price or 0)

            # حساب عدد الأيام منذ آخر حركة
            days_since_last_movement = None
            if movements:
                last_movement_date = movements[-1].movement_date
                days_since_last_movement = (datetime.now().date() - last_movement_date).days

            # حساب معدل الاستهلاك (إذا توفرت بيانات كافية)
            consumption_rate = 0
            if len(movements) >= 2:
                out_movements = [m for m in movements if m.movement_type in ['out', 'sale']]
                if out_movements:
                    total_out_quantity = sum(m.quantity for m in out_movements)
                    days_range = (movements[0].movement_date - movements[-1].movement_date).days
                    if days_range > 0:
                        consumption_rate = total_out_quantity / days_range

            # تقدير عدد الأيام المتبقية
            days_remaining = None
            if consumption_rate > 0:
                days_remaining = int(current_quantity / consumption_rate)

            product_dict = {
                'id': product.id,
                'name': product.name,
                'code': product.code,
                'unit': product.unit,
                'current_quantity': current_quantity,
                'calculated_quantity': calculated_quantity,
                'registered_quantity': product.quantity,
                'total_in': total_in,
                'total_out': total_out,
                'min_quantity': product.min_quantity,
                'shortage': shortage,
                'shortage_percentage': shortage_percentage,
                'required_quantity': required_quantity,
                'estimated_cost': estimated_cost,
                'urgency_level': urgency_level,
                'urgency_text': urgency_text,
                'urgency_color': urgency_color,
                'priority': priority,
                'warehouse': product.warehouse,
                'warehouse_name': product.warehouse.name if product.warehouse else 'غير محدد',
                'warehouse_id': product.warehouse_id,
                'cost_price': product.cost_price or 0,
                'selling_price': product.selling_price or 0,
                'category': product.category or 'غير محدد',
                'last_movement_date': movements[-1].movement_date if movements else None,
                'days_since_last_movement': days_since_last_movement,
                'consumption_rate': round(consumption_rate, 2) if consumption_rate else 0,
                'days_remaining': days_remaining,
                'total_movements': len(movements),
                'is_out_of_stock': is_out_of_stock,
                'is_critical': is_critical,
                'is_very_low': is_very_low,
                'created_at': product.created_at.strftime('%Y-%m-%d') if product.created_at else None
            }
            enhanced_low_stock.append(product_dict)

    # ترتيب المنتجات حسب الأولوية والنقص
    enhanced_low_stock.sort(key=lambda x: (x['priority'], x['shortage_percentage']), reverse=True)

    # تحديد العدد المعروض في لوحة التحكم (أول 10 منتجات)
    low_stock_products = enhanced_low_stock[:10]
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_invoices=recent_invoices,
                         low_stock_products=low_stock_products)

# مسارات العملاء
@app.route('/customers')
def customers():
    """صفحة العملاء"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Customer.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Customer.name.contains(search),
                Customer.phone.contains(search),
                Customer.email.contains(search)
            )
        )
    
    customers = query.order_by(Customer.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('customers/list.html', customers=customers, search=search)

@app.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    """إضافة عميل جديد"""
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            tax_number=request.form.get('tax_number'),
            credit_limit=float(request.form.get('credit_limit', 0)),
            notes=request.form.get('notes')
        )
        
        try:
            db.session.add(customer)
            db.session.commit()
            flash('تم إضافة العميل بنجاح', 'success')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء إضافة العميل', 'error')
    
    return render_template('customers/add.html')

@app.route('/customers/<int:id>/edit', methods=['GET', 'POST'])
def edit_customer(id):
    """تعديل عميل"""
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.phone = request.form.get('phone')
        customer.email = request.form.get('email')
        customer.address = request.form.get('address')
        customer.tax_number = request.form.get('tax_number')
        customer.credit_limit = float(request.form.get('credit_limit', 0))
        customer.notes = request.form.get('notes')
        customer.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('تم تحديث بيانات العميل بنجاح', 'success')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء تحديث بيانات العميل', 'error')
    
    return render_template('customers/edit.html', customer=customer)

@app.route('/customers/<int:id>/delete', methods=['POST'])
def delete_customer(id):
    """حذف عميل"""
    customer = Customer.query.get_or_404(id)
    
    # التحقق من وجود فواتير مرتبطة
    if customer.invoices:
        flash('لا يمكن حذف العميل لوجود فواتير مرتبطة به', 'error')
        return redirect(url_for('customers'))
    
    try:
        customer.is_active = False
        db.session.commit()
        flash('تم حذف العميل بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء حذف العميل', 'error')
    
    return redirect(url_for('customers'))

# مسارات API للعملات والإعدادات
@app.route('/api/currencies')
def get_currencies():
    """الحصول على جميع العملات"""
    currencies = CurrencySettings.query.filter_by(is_active=True).all()
    return jsonify([{
        'code': c.currency_code,
        'name': c.currency_name,
        'symbol': c.currency_symbol,
        'rate': c.exchange_rate,
        'is_base': c.is_base_currency
    } for c in currencies])

@app.route('/api/settings')
def get_settings():
    """الحصول على إعدادات الشركة"""
    settings = CompanySettings.query.all()
    return jsonify({s.setting_key: s.setting_value for s in settings})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """تحديث إعدادات الشركة"""
    data = request.get_json()

    for key, value in data.items():
        setting = CompanySettings.query.filter_by(setting_key=key).first()
        if setting:
            setting.setting_value = str(value)
        else:
            setting = CompanySettings(
                setting_key=key,
                setting_value=str(value),
                setting_type='string'
            )
            db.session.add(setting)

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم حفظ الإعدادات بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/exchange-rates', methods=['POST'])
def update_exchange_rates():
    """تحديث أسعار الصرف"""
    data = request.get_json()

    try:
        for currency_code, rate in data.items():
            currency = CurrencySettings.query.filter_by(currency_code=currency_code).first()
            if currency:
                currency.exchange_rate = float(rate)

        db.session.commit()
        return jsonify({'success': True, 'message': 'تم تحديث أسعار الصرف بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# مسارات API للتقارير المحسنة
@app.route('/api/journal-entries')
def get_journal_entries():
    """الحصول على قيود دفتر اليومية مع فلترة العملة"""
    currency = request.args.get('currency', 'all')
    entry_type = request.args.get('type', 'all')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = JournalEntry.query

    if currency != 'all':
        query = query.filter(JournalEntry.currency == currency)

    if entry_type != 'all':
        query = query.filter(JournalEntry.entry_type == entry_type)

    if date_from:
        query = query.filter(JournalEntry.entry_date >= date_from)

    if date_to:
        query = query.filter(JournalEntry.entry_date <= date_to)

    entries = query.order_by(JournalEntry.entry_date.desc()).all()

    return jsonify([{
        'id': e.id,
        'date': e.entry_date.strftime('%Y-%m-%d'),
        'type': e.entry_type,
        'description': e.description,
        'debit_account': e.debit_account,
        'credit_account': e.credit_account,
        'debit_amount': e.debit_amount,
        'credit_amount': e.credit_amount,
        'currency': e.currency,
        'reference_type': e.reference_type,
        'reference_id': e.reference_id
    } for e in entries])

@app.route('/api/balances')
def get_balances():
    """الحصول على الأرصدة الإجمالية لكل عملة"""
    balances = {}
    currencies = CurrencySettings.query.filter_by(is_active=True).all()

    for currency in currencies:
        code = currency.currency_code

        # حساب أرصدة العملاء
        customer_balance = 0
        customer_invoices = Invoice.query.filter(
            Invoice.invoice_type == 'sale',
            Invoice.status == 'confirmed',
            Invoice.currency == code
        ).all()

        for inv in customer_invoices:
            customer_balance += inv.remaining_amount or 0

        # حساب أرصدة الموردين
        supplier_balance = 0
        supplier_invoices = Invoice.query.filter(
            Invoice.invoice_type == 'purchase',
            Invoice.status == 'confirmed',
            Invoice.currency == code
        ).all()

        for inv in supplier_invoices:
            supplier_balance += inv.remaining_amount or 0

        # حساب رصيد الصندوق والبنك
        cash_balance = 0
        bank_balance = 0

        payments = Payment.query.filter(
            Payment.status == 'confirmed',
            Payment.currency == code
        ).all()

        for payment in payments:
            amount = payment.amount or 0
            if payment.payment_method == 'cash':
                if payment.payment_type == 'receipt':
                    cash_balance += amount
                else:
                    cash_balance -= amount
            elif payment.payment_method == 'bank':
                if payment.payment_type == 'receipt':
                    bank_balance += amount
                else:
                    bank_balance -= amount

        balances[code] = {
            'currency_name': currency.currency_name,
            'currency_symbol': currency.currency_symbol,
            'customer_balance': customer_balance,
            'supplier_balance': supplier_balance,
            'cash_balance': cash_balance,
            'bank_balance': bank_balance,
            'net_balance': customer_balance - supplier_balance + cash_balance + bank_balance
        }

    return jsonify(balances)

@app.route('/api/low-stock-products')
def get_low_stock_products():
    """الحصول على جميع المنتجات منخفضة المخزون مع تفاصيل شاملة"""
    try:
        # الحصول على جميع المنتجات النشطة مع الحد الأدنى المحدد
        active_products = Product.query.filter(
            Product.is_active == True,
            Product.min_quantity > 0
        ).all()

        enhanced_low_stock = []

        for product in active_products:
            # حساب الكمية الفعلية من حركات المخزون
            movements = InventoryMovement.query.filter_by(
                product_id=product.id,
                warehouse_id=product.warehouse_id
            ).order_by(InventoryMovement.movement_date.desc()).all()

            calculated_quantity = 0
            for movement in movements:
                if movement.movement_type in ['in', 'adjustment']:
                    if movement.movement_type == 'adjustment' and movement.quantity < 0:
                        calculated_quantity -= abs(movement.quantity)
                    else:
                        calculated_quantity += movement.quantity
                elif movement.movement_type in ['out', 'sale']:
                    calculated_quantity -= movement.quantity

            # استخدام الكمية المحسوبة أو الكمية المسجلة
            current_quantity = max(calculated_quantity, product.quantity)

            # التحقق من نقص المخزون
            is_low_stock = current_quantity <= product.min_quantity

            if is_low_stock:
                is_critical = current_quantity <= (product.min_quantity * 0.5)
                is_out_of_stock = current_quantity <= 0

                # حساب نسبة النقص والأولوية
                shortage = max(0, product.min_quantity - current_quantity)
                shortage_percentage = round((shortage / product.min_quantity * 100), 1) if product.min_quantity > 0 else 0

                # تحديد مستوى الخطورة
                if is_out_of_stock:
                    urgency_level = 'critical'
                    urgency_text = 'نفد المخزون'
                    urgency_color = 'danger'
                    priority = 1
                elif is_critical:
                    urgency_level = 'high'
                    urgency_text = 'حرج جداً'
                    urgency_color = 'danger'
                    priority = 2
                elif current_quantity <= (product.min_quantity * 0.8):
                    urgency_level = 'medium'
                    urgency_text = 'منخفض'
                    urgency_color = 'warning'
                    priority = 3
                else:
                    urgency_level = 'low'
                    urgency_text = 'تحذير'
                    urgency_color = 'info'
                    priority = 4

                # حساب الكمية المطلوبة للوصول للحد الآمن
                safe_quantity = product.min_quantity * 1.5
                required_quantity = max(0, safe_quantity - current_quantity)

                # تقدير التكلفة المطلوبة
                estimated_cost = required_quantity * (product.cost_price or 0)

                product_dict = {
                    'id': product.id,
                    'name': product.name,
                    'code': product.code,
                    'unit': product.unit,
                    'current_quantity': current_quantity,
                    'min_quantity': product.min_quantity,
                    'shortage': shortage,
                    'shortage_percentage': shortage_percentage,
                    'required_quantity': required_quantity,
                    'estimated_cost': estimated_cost,
                    'urgency_level': urgency_level,
                    'urgency_text': urgency_text,
                    'urgency_color': urgency_color,
                    'priority': priority,
                    'warehouse_id': product.warehouse_id,
                    'warehouse_name': product.warehouse.name if product.warehouse else 'غير محدد',
                    'cost_price': product.cost_price or 0,
                    'selling_price': product.selling_price or 0,
                    'category': product.category or 'غير محدد',
                    'last_movement_date': movements[0].movement_date.strftime('%Y-%m-%d') if movements else None,
                    'is_out_of_stock': is_out_of_stock,
                    'is_critical': is_critical,
                    'created_at': product.created_at.strftime('%Y-%m-%d') if product.created_at else None
                }
                enhanced_low_stock.append(product_dict)

        # ترتيب المنتجات حسب الأولوية والنقص
        enhanced_low_stock.sort(key=lambda x: (x['priority'], -x['shortage_percentage']))

        return jsonify({
            'success': True,
            'products': enhanced_low_stock,
            'total_count': len(enhanced_low_stock),
            'critical_count': len([p for p in enhanced_low_stock if p['urgency_level'] == 'critical']),
            'high_count': len([p for p in enhanced_low_stock if p['urgency_level'] == 'high']),
            'medium_count': len([p for p in enhanced_low_stock if p['urgency_level'] == 'medium']),
            'low_count': len([p for p in enhanced_low_stock if p['urgency_level'] == 'low']),
            'total_estimated_cost': sum([p['estimated_cost'] for p in enhanced_low_stock])
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# وظائف تصدير PDF محسنة
def format_arabic_text(text):
    """تنسيق النص العربي للعرض الصحيح في PDF"""
    if not text:
        return ""
    try:
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)
    except:
        return str(text)

def format_date_arabic(date_obj):
    """تنسيق التاريخ بالشكل العربي dd/mm/yyyy"""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        except:
            return date_obj

    if isinstance(date_obj, datetime):
        return date_obj.strftime('%d/%m/%Y')
    elif isinstance(date_obj, date):
        return date_obj.strftime('%d/%m/%Y')
    else:
        return str(date_obj)

@app.route('/api/export/journal-pdf')
def export_journal_pdf():
    """تصدير دفتر اليومية إلى PDF"""
    try:
        # الحصول على المعاملات
        currency = request.args.get('currency', 'all')
        entry_type = request.args.get('type', 'all')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        query = JournalEntry.query

        if currency != 'all':
            query = query.filter(JournalEntry.currency == currency)
        if entry_type != 'all':
            query = query.filter(JournalEntry.entry_type == entry_type)
        if date_from:
            query = query.filter(JournalEntry.entry_date >= date_from)
        if date_to:
            query = query.filter(JournalEntry.entry_date <= date_to)

        entries = query.order_by(JournalEntry.entry_date.desc()).all()

        # إنشاء PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)

        # إعداد الأنماط
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # وسط
            fontName='Helvetica-Bold'
        )

        # المحتوى
        story = []

        # العنوان
        title = format_arabic_text("دفتر اليومية العام")
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

        # معلومات التقرير
        info_text = f"تاريخ التقرير: {format_date_arabic(datetime.now())}"
        if date_from and date_to:
            info_text += f" | الفترة: من {format_date_arabic(date_from)} إلى {format_date_arabic(date_to)}"
        if currency != 'all':
            info_text += f" | العملة: {currency}"

        story.append(Paragraph(format_arabic_text(info_text), styles['Normal']))
        story.append(Spacer(1, 12))

        # الجدول
        if entries:
            data = [['التاريخ', 'النوع', 'الوصف', 'المدين', 'الدائن', 'العملة']]

            total_debit = 0
            total_credit = 0

            for entry in entries:
                data.append([
                    format_date_arabic(entry.entry_date),
                    format_arabic_text(entry.entry_type or ''),
                    format_arabic_text(entry.description or ''),
                    f"{entry.debit_amount or 0:,.0f}",
                    f"{entry.credit_amount or 0:,.0f}",
                    entry.currency or 'SYP'
                ])
                total_debit += entry.debit_amount or 0
                total_credit += entry.credit_amount or 0

            # إضافة صف الإجماليات
            data.append([
                format_arabic_text('الإجمالي'),
                '', '',
                f"{total_debit:,.0f}",
                f"{total_credit:,.0f}",
                ''
            ])

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
        else:
            story.append(Paragraph(format_arabic_text("لا توجد قيود في الفترة المحددة"), styles['Normal']))

        # بناء PDF
        doc.build(story)
        buffer.seek(0)

        # إرسال الملف
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=journal_{datetime.now().strftime("%Y%m%d")}.pdf'

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/balances-pdf')
def export_balances_pdf():
    """تصدير تقرير الأرصدة إلى PDF"""
    try:
        # الحصول على الأرصدة
        balances = {}
        currencies = CurrencySettings.query.filter_by(is_active=True).all()

        for currency in currencies:
            code = currency.currency_code

            # حساب الأرصدة (نفس المنطق من get_balances)
            customer_balance = 0
            customer_invoices = Invoice.query.filter(
                Invoice.invoice_type == 'sale',
                Invoice.status == 'confirmed',
                Invoice.currency == code
            ).all()

            for inv in customer_invoices:
                customer_balance += inv.remaining_amount or 0

            supplier_balance = 0
            supplier_invoices = Invoice.query.filter(
                Invoice.invoice_type == 'purchase',
                Invoice.status == 'confirmed',
                Invoice.currency == code
            ).all()

            for inv in supplier_invoices:
                supplier_balance += inv.remaining_amount or 0

            cash_balance = 0
            bank_balance = 0

            payments = Payment.query.filter(
                Payment.status == 'confirmed',
                Payment.currency == code
            ).all()

            for payment in payments:
                amount = payment.amount or 0
                if payment.payment_method == 'cash':
                    if payment.payment_type == 'receipt':
                        cash_balance += amount
                    else:
                        cash_balance -= amount
                elif payment.payment_method == 'bank':
                    if payment.payment_type == 'receipt':
                        bank_balance += amount
                    else:
                        bank_balance -= amount

            balances[code] = {
                'currency_name': currency.currency_name,
                'currency_symbol': currency.currency_symbol,
                'customer_balance': customer_balance,
                'supplier_balance': supplier_balance,
                'cash_balance': cash_balance,
                'bank_balance': bank_balance,
                'net_balance': customer_balance - supplier_balance + cash_balance + bank_balance
            }

        # إنشاء PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,
            fontName='Helvetica-Bold'
        )

        story = []

        # العنوان
        title = format_arabic_text("تقرير أرصدة العملاء والموردين")
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

        # معلومات التقرير
        info_text = f"تاريخ التقرير: {format_date_arabic(datetime.now())}"
        story.append(Paragraph(format_arabic_text(info_text), styles['Normal']))
        story.append(Spacer(1, 12))

        # الجدول
        if balances:
            data = [['العملة', 'أرصدة العملاء', 'أرصدة الموردين', 'رصيد الصندوق', 'رصيد البنك', 'الصافي']]

            for code, balance in balances.items():
                data.append([
                    format_arabic_text(f"{balance['currency_name']} ({balance['currency_symbol']})"),
                    f"{balance['customer_balance']:,.0f}",
                    f"{balance['supplier_balance']:,.0f}",
                    f"{balance['cash_balance']:,.0f}",
                    f"{balance['bank_balance']:,.0f}",
                    f"{balance['net_balance']:,.0f}"
                ])

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
        else:
            story.append(Paragraph(format_arabic_text("لا توجد أرصدة للعرض"), styles['Normal']))

        # بناء PDF
        doc.build(story)
        buffer.seek(0)

        # إرسال الملف
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=balances_{datetime.now().strftime("%Y%m%d")}.pdf'

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
