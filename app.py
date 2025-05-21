from flask import Flask, render_template, request, flash, redirect, session, url_for, abort, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
from hashlib import md5
from  sqlalchemy.sql.expression import func
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqlamodel import ModelView
from flask_admin import Admin
import os
from urllib.parse import quote
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.colors import black


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['UPLOAD_FOLDER'] = 'static/img/upload'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
db = SQLAlchemy(app)
ckeditor = CKEditor(app)


class Users(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100), unique=True)
    root = db.Column(db.Integer, default=0)
    
    reports = db.relationship('Reports', backref='user', lazy=True)
       
    def __repr__(self):
        return 'User %r' % self.id 
    

class Products(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(100))
    subText = db.Column(db.Text)
    text = db.Column(db.Text)
    image_name = db.Column(db.String(100))
    category = db.Column(db.String(100))
    price = db.Column(db.Integer)
    
    orders = db.relationship('Orders', backref='product', lazy=True)
    
    def __repr__(self):
        return 'Products %r' % self.id 
    

class Orders(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('users.id'))
    id_product = db.Column(db.Integer, db.ForeignKey('products.id'))
    count_products = db.Column(db.Integer)
    status = db.Column(db.Integer, default=0)
    address = db.Column(db.String(500))
    date = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return 'Orders %r' % self.id
    
    
class Reports(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('users.id'))
    pdf = db.Column(db.String(500))

    def __repr__(self):
        return 'Reports %r' % self.id


class AdminIndex(AdminIndexView):
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if 'name' in session:
            user = Users.query.filter_by(email=session['name']).first()
            if user.root!=1:
                abort(403)
            else:
                return self.render('admin/dashboard_index.html')
        else:
            abort(401)


admin = Admin(app, name='Эко-ферма',index_view=AdminIndex(), template_mode='bootstrap4')


class OrdersView(ModelView):
    column_display_pk = True 
    column_hide_backrefs = False
    column_list = ['id','id_user','id_product', 'count_products', 'status', 'date']


class ReportsView(ModelView):
    column_display_pk = True 
    column_hide_backrefs = False
    column_list = ['id','id_user','pdf']


admin.add_view(ModelView(Users, db.session))
admin.add_view(ModelView(Products, db.session))
admin.add_view(OrdersView(Orders, db.session))
admin.add_view(ReportsView(Reports, db.session))


@app.route('/', methods=['GET', 'POST'])
def index():
    random_products = Products.query.order_by(func.random()).limit(4).all()
    return render_template("index.html",random_products=random_products)


PER_PAGE = 9


@app.route('/catalog', methods=['GET', 'POST'])
def catalog():
    page = request.args.get('page', 1, type=int)
    products_query = Products.query
    
    # Фильтрация
    category = request.args.get('category')
    search = request.args.get('search')
    maxprice = request.args.get('maxprice')
    
    if category:
        category = category.capitalize()
        category = "%{}%".format(category)
        products_query = products_query.filter(Products.category.ilike(category))
    
    if maxprice:
        products_query = products_query.filter(Products.price <= maxprice)
    
    if search:
        products_query = products_query.filter(Products.title.ilike(f'%{search}%'))
    
    # Пагинация
    products = products_query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    max_price = db.session.query(func.max(Products.price)).scalar()



    if request.method == 'POST':
        title = request.form.get('title')
        subText = request.form.get('subText')
        category = request.form.get('category')
        price = request.form.get('price')
        image = request.files['image']
        filename = secure_filename(image.filename)
        pic_name = str(uuid.uuid4()) + "_" + filename
        image.save("static/img/upload/" + pic_name)
        text = request.form.get('ckeditor')
        product = Products(title=title,subText=subText,category=category,price=price,image_name=pic_name,text=text)
        db.session.add(product)
        db.session.commit()
        flash("Запись добавлена!", category="ok")
        return redirect(url_for("catalog"))
    
 
    
    return render_template("catalog.html",products=products,max_price=max_price)


@app.route('/product/<int:id>', methods=['GET', 'POST'])
def product(id):
    product = Products.query.get(id)
    if request.method == 'POST':
        product.title = request.form.get('title')
        product.category = request.form.get('category')
        product.price = request.form.get('price')
        product.text = request.form.get('ckeditor')
        product.subText= request.form.get('subText')
        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            pic_name = str(uuid.uuid4()) + "_" + filename
            image.save("static/img/upload/" + pic_name)
            product.image_name = pic_name
        db.session.commit()
        flash("Запись обновлена!", category="ok")
        return redirect(url_for("product", id=product.id))
    return render_template("product.html",product=product)


@app.route('/delete-product/<int:id>')
def delete_article(id):
    obj = Products.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    flash("Запись удалена!", category="bad")
    return redirect('/catalog')


@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if 'name' not in session:
        abort(401)  # Пользователь не авторизован

    orders = []
    total_sum = 0

    
    total_user = Users.query.filter_by(email=session['name']).first()
    if not total_user:
        abort(404, description="User not found")
    reports = Reports.query.filter_by(id_user=total_user.id).all()
    # Для GET-запроса
    orders = Orders.query.filter_by(id_user=total_user.id).join(Products).all()
    total_sum = (
        db.session.query(func.sum(Products.price * Orders.count_products))
        .join(Orders, Products.id == Orders.id_product)
        .filter(Orders.id_user == total_user.id)
        .filter(Orders.status == 0)
        .scalar()
    )

    return render_template("cart.html", orders=orders, total_sum=total_sum,reports=reports)


@app.route('/buy_all', methods=['GET', 'POST'])
def buy_all():
    if not 'name' in session:
        abort(401)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"report_{timestamp}.pdf"
    email = request.form.get('email')
    phone_number = request.form.get('phone_number')
    address = request.form.get('address')
    total_user = Users.query.filter_by(email=session['name']).first()
    
    # Получаем заказы с фильтром по status == 0
    orders = Orders.query.filter_by(id_user=total_user.id).join(Products).filter(Orders.status == 0).all()
    
    # Вычисляем общую сумму
    total_sum = (
        db.session.query(func.sum(Products.price * Orders.count_products))
        .join(Orders, Products.id == Orders.id_product)
        .filter(Orders.id_user == total_user.id, Orders.status == 0)
        .scalar()
    ) 
    
    flash("Заказ оформлен! Можете просмотреть чек!", category="ok")
    PDF_FOLDER = "static/pdf_reports"
    
    # Регистрируем шрифт Roboto
    pdfmetrics.registerFont(TTFont('Roboto', 'static/fonts/Roboto-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Roboto-Bold', 'static/fonts/Roboto-Bold.ttf'))  # Жирный шрифт для заголовков
    
    # Создание папки, если её нет
    if not os.path.exists(PDF_FOLDER):
        os.makedirs(PDF_FOLDER)
        
    pdf_path = os.path.join(PDF_FOLDER, pdf_filename)    
    
    # Создание PDF с использованием ReportLab
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    
    # Устанавливаем название PDF-документа
    c.setTitle(f"Чек заказа от {timestamp}")
    
    # Шапка документа
    c.setFont("Roboto-Bold", 18)
    c.drawString(50, height - 30, "Эко-Ферма")  # Название сайта
    c.line(50, height - 35, width - 50, height - 35)  # Горизонтальная линия
    
    # Основная информация
    c.setFont("Roboto", 12)
    y_position = height - 60  # Начальная позиция для вывода информации
    c.drawString(50, y_position, f"Email: {email}")
    y_position -= 20
    c.drawString(50, y_position, f"Контактный номер: {phone_number}")
    y_position -= 20
    c.drawString(50, y_position, f"Адрес доставки: {address}")
    y_position -= 20
    c.drawString(50, y_position, f"Общая сумма: {total_sum} руб.")
    y_position -= 30  # Дополнительный отступ перед списком заказов
    
    # Заголовок для списка заказов
    c.setFont("Roboto-Bold", 14)
    c.drawString(50, y_position, "Ваши заказы:")
    c.line(50, y_position - 5, width - 50, y_position - 5)  # Горизонтальная линия
    y_position -= 20
    
    # Добавляем информацию о заказах с фильтром по status == 0
    for i, order in enumerate(orders):
        if order.status == 0:  # Фильтруем по статусу продукта
            c.setFont("Roboto", 12)
            # Переносим длинные строки на новую строку
            product_info = f"Товар: {order.product.title}, Количество: {order.count_products}, Цена: {order.product.price} руб."
            lines = []
            max_line_length = 80  # Максимальная длина строки
            while len(product_info) > max_line_length:
                space_index = product_info[:max_line_length].rfind(' ')
                if space_index == -1:
                    space_index = max_line_length
                lines.append(product_info[:space_index])
                product_info = product_info[space_index:].strip()
            lines.append(product_info)
            
            for line in lines:
                c.drawString(50, y_position, line)
                y_position -= 15  # Отступ между строками
            y_position -= 5  # Дополнительный отступ между заказами
    
    # Подвал документа
    c.setFont("Roboto", 10)
    y_position = 50  # Позиция для подвала
    c.line(50, y_position, width - 50, y_position)  # Горизонтальная линия
    y_position -= 10
    c.drawString(50, y_position, "Контакты:")
    y_position -= 10
    c.drawString(50, y_position, "Адрес: ул. Курчатова, 4, г. Гродно, Беларусь")
    y_position -= 10
    c.drawString(50, y_position, "Телефон: +375 (29) 111-22-33")
    y_position -= 10
    c.drawString(50, y_position, "Email: info@eco-ferma.by")
    y_position -= 10
    c.drawString(width - 100, y_position, "2025 год")  # Год в правом нижнем углу
    
    c.save()
    
    # Сохраняем отчет в базе данных
    report = Reports(id_user=total_user.id, pdf=pdf_filename)
    db.session.add(report)
    db.session.commit()
    
    # Подготавливаем PDF для отправки пользователю
    encoded_filename = quote(pdf_filename)
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'
        
    # Обновляем статус заказов
    Orders.query.filter_by(id_user=total_user.id).update({Orders.status: 1})
    db.session.commit()
    
    return redirect('/cart')


@app.route('/add_to_cart/<int:id_user>/<int:id_product>', methods=['GET', 'POST'])
def add_to_cart(id_user,id_product):
    if request.method == 'POST':
        count_products = request.form.get('count_products')
        order = Orders(count_products=count_products,id_user=id_user,id_product=id_product)
        db.session.add(order)
        db.session.commit()
    flash("Заказ оформлен!", category="ok")
    return redirect(url_for("product", id=id_product))


@app.route('/about', methods=['GET', 'POST'])
def about():
    return render_template("about.html")


@app.route('/services', methods=['GET', 'POST'])
def services():
    return render_template("services.html")


@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    return render_template("contacts.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    session.pop('name', None)
    if request.method == 'POST':
        email = request.form.get('email')
        password = md5(request.form.get('password').encode()).hexdigest()
        user = Users.query.filter_by(email=email,password=password).first()
        if user:
            session['name'] = Users.query.filter_by(email=email).first().email
            return redirect(url_for("index"))
        else:
            flash("Неправильная почта или пароль!", category="bad")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route('/reg', methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            surname = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            user = Users(name=name,surname=surname,email=email,password=md5(password.encode()).hexdigest())
            db.session.add(user)
            db.session.commit()
            flash("Регистрация прошла успешно!", category="ok")
            return redirect(url_for("reg"))
        except:
            flash("Произошла ошибка! Проверьте введенные данные!", category="bad")
            db.session.rollback()
            return redirect(url_for("reg"))
    return render_template("reg.html")


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidded(e):
    return render_template('403.html'), 403


@app.errorhandler(401)
def forbidded(e):
    return render_template('401.html'), 401


@app.route('/logout')
def logout():
    session.pop('name', None)
    return redirect('/')


@app.route('/delete-order/<int:id>')
def delete_order(id):
    obj = Orders.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    flash("Запись удалена!", category="bad")
    return redirect('/cart')




    
@app.context_processor
def inject_order_count():
    order_count = 0
    if 'name' in session:
        user = object
        user = Users.query.filter_by(email=session['name']).first()
        order_count = db.session.query(func.count(Orders.id)) \
                    .filter_by(id_user=user.id) \
                    .filter(Orders.status == 0) \
                    .scalar()   
    
    return dict(order_count=order_count)


@app.context_processor
def inject_user():
    def get_user_name():
        if 'name' in session:
            return Users.query.filter_by(email=session['name']).first()
    return dict(active_user=get_user_name())


if __name__ == '__main__':
    app.run(debug=True)