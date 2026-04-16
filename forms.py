"""
Forms for the Delivery System Application
WTForms validation for all user input forms
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, EmailField, TextAreaField, SelectField, IntegerField, FloatField, DateField, TelField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError
from models import Admin, Driver, Customer


class LoginForm(FlaskForm):
    """Generic login form"""
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')


class AdminLoginForm(LoginForm):
    """Admin specific login form"""
    pass


class DriverLoginForm(LoginForm):
    """Driver login form using email"""
    pass


class CustomerLoginForm(LoginForm):
    """Customer login form"""
    pass


class DriverRegistrationForm(FlaskForm):
    """Driver registration form"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone = TelField('Phone Number', validators=[DataRequired(), Length(min=10, max=20)])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    license_number = StringField('License Number', validators=[DataRequired(), Length(min=5, max=50)])
    vehicle_type = SelectField('Vehicle Type', choices=[
        ('motorcycle', 'Motorcycle'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('truck', 'Truck')
    ], validators=[DataRequired()])
    vehicle_plate = StringField('Vehicle Plate', validators=[DataRequired(), Length(min=5, max=20)])
    service_type = SelectField('Service Type', choices=[
        ('Package', 'Package Delivery'),
        ('Human Transportation', 'Human Transportation'),
        ('Both', 'Both Services')
    ], validators=[DataRequired()])
    
    def validate_email(self, email):
        if Driver.query.filter_by(email=email.data).first():
            raise ValidationError('Email already registered')
    
    def validate_license_number(self, license_number):
        if Driver.query.filter_by(license_number=license_number.data).first():
            raise ValidationError('License number already registered')


class CustomerRegistrationForm(FlaskForm):
    """Customer registration form"""
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone = TelField('Phone Number', validators=[DataRequired(), Length(min=10, max=20)])
    address = StringField('Default Address', validators=[Optional(), Length(max=255)])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    
    def validate_email(self, email):
        if Customer.query.filter_by(email=email.data).first():
            raise ValidationError('Email already registered')


class DriverApprovalForm(FlaskForm):
    """Form for approving/rejecting drivers"""
    action = SelectField('Action', choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('suspend', 'Suspend')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])


class OrderForm(FlaskForm):
    """Order creation form"""
    customer_id = IntegerField('Customer ID', validators=[DataRequired()])
    pickup_address = TextAreaField('Pickup Address', validators=[DataRequired()])
    delivery_address = TextAreaField('Delivery Address', validators=[DataRequired()])
    package_description = StringField('Package Description', validators=[DataRequired(), Length(max=200)])
    weight = FloatField('Weight (kg)', validators=[DataRequired(), NumberRange(min=0.1, max=100)])
    priority = SelectField('Priority', choices=[
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('urgent', 'Urgent')
    ], default='standard')
    notes = TextAreaField('Notes', validators=[Optional()])


class DriverStatusForm(FlaskForm):
    """Form for updating driver status"""
    status = SelectField('Status', choices=[
        ('Active', 'Active'),
        ('Suspended', 'Suspended'),
        ('Pending', 'Pending')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])


class AdminCreationForm(FlaskForm):
    """Form for creating new admin users"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=120)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    
    # Permissions
    can_manage_drivers = BooleanField('Can Manage Drivers')
    can_view_analytics = BooleanField('Can View Analytics')
    can_manage_orders = BooleanField('Can Manage Orders')
    can_manage_admins = BooleanField('Can Manage Admins')
    
    def validate_username(self, username):
        if Admin.query.filter_by(username=username.data).first():
            raise ValidationError('Username already taken')
    
    def validate_email(self, email):
        if Admin.query.filter_by(email=email.data).first():
            raise ValidationError('Email already registered')


class SearchForm(FlaskForm):
    """Generic search form"""
    query = StringField('Search', validators=[DataRequired()])
    filters = SelectField('Filters', choices=[
        ('all', 'All'),
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('suspended', 'Suspended')
    ], default='all')
