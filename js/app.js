/**
 * برنامج المحاسب الذكي - SAM PRO
 * تطوير: MOHANNAD AHMAD
 * ملف JavaScript الرئيسي
 */

// تهيئة التطبيق عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * تهيئة التطبيق
 */
function initializeApp() {
    // تفعيل التلميحات
    initializeTooltips();
    
    // تفعيل النوافذ المنبثقة
    initializeModals();
    
    // تفعيل التحقق من النماذج
    initializeFormValidation();
    
    // تفعيل تنسيق الأرقام
    initializeNumberFormatting();
    
    // تفعيل البحث المباشر
    initializeLiveSearch();
    
    // تفعيل الرسوم المتحركة
    initializeAnimations();
    
    console.log('تم تهيئة برنامج المحاسب الذكي بنجاح');
}

/**
 * تفعيل التلميحات
 */
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * تفعيل النوافذ المنبثقة
 */
function initializeModals() {
    // إغلاق النوافذ المنبثقة عند الضغط على Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            var modals = document.querySelectorAll('.modal.show');
            modals.forEach(function(modal) {
                var modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });
}

/**
 * تفعيل التحقق من النماذج
 */
function initializeFormValidation() {
    // التحقق من النماذج عند الإرسال
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // التحقق من الحقول المطلوبة
    var requiredFields = document.querySelectorAll('input[required], select[required], textarea[required]');
    requiredFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            validateField(field);
        });
    });
}

/**
 * التحقق من صحة حقل معين
 */
function validateField(field) {
    var isValid = true;
    var errorMessage = '';
    
    // التحقق من الحقول المطلوبة
    if (field.hasAttribute('required') && !field.value.trim()) {
        isValid = false;
        errorMessage = 'هذا الحقل مطلوب';
    }
    
    // التحقق من البريد الإلكتروني
    if (field.type === 'email' && field.value) {
        var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(field.value)) {
            isValid = false;
            errorMessage = 'يرجى إدخال بريد إلكتروني صحيح';
        }
    }
    
    // التحقق من الأرقام
    if (field.type === 'number' && field.value) {
        var value = parseFloat(field.value);
        if (isNaN(value)) {
            isValid = false;
            errorMessage = 'يرجى إدخال رقم صحيح';
        }
        
        if (field.hasAttribute('min') && value < parseFloat(field.getAttribute('min'))) {
            isValid = false;
            errorMessage = `القيمة يجب أن تكون أكبر من أو تساوي ${field.getAttribute('min')}`;
        }
        
        if (field.hasAttribute('max') && value > parseFloat(field.getAttribute('max'))) {
            isValid = false;
            errorMessage = `القيمة يجب أن تكون أقل من أو تساوي ${field.getAttribute('max')}`;
        }
    }
    
    // عرض رسالة الخطأ
    showFieldError(field, isValid, errorMessage);
    
    return isValid;
}

/**
 * عرض رسالة خطأ للحقل
 */
function showFieldError(field, isValid, errorMessage) {
    // إزالة الرسائل السابقة
    var existingError = field.parentNode.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
    
    // إزالة الفئات السابقة
    field.classList.remove('is-valid', 'is-invalid');
    
    if (!isValid) {
        // إضافة فئة الخطأ
        field.classList.add('is-invalid');
        
        // إنشاء رسالة الخطأ
        var errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = errorMessage;
        field.parentNode.appendChild(errorDiv);
    } else {
        // إضافة فئة النجاح
        field.classList.add('is-valid');
    }
}

/**
 * تفعيل تنسيق الأرقام
 */
function initializeNumberFormatting() {
    // تنسيق حقول الأرقام
    var numberFields = document.querySelectorAll('input[type="number"]');
    numberFields.forEach(function(field) {
        field.addEventListener('input', function() {
            formatNumber(field);
        });
    });
    
    // تنسيق الأرقام في الجداول
    var numberCells = document.querySelectorAll('.format-number');
    numberCells.forEach(function(cell) {
        var value = parseFloat(cell.textContent);
        if (!isNaN(value)) {
            cell.textContent = formatCurrency(value);
        }
    });
}

/**
 * تنسيق الأرقام
 */
function formatNumber(field) {
    var value = field.value.replace(/[^\d.-]/g, '');
    if (value && !isNaN(value)) {
        field.value = value;
    }
}

/**
 * تنسيق العملة
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('ar-SY', {
        style: 'currency',
        currency: 'SYP',
        minimumFractionDigits: 2
    }).format(amount);
}

/**
 * تفعيل البحث المباشر
 */
function initializeLiveSearch() {
    var searchInputs = document.querySelectorAll('.live-search');
    searchInputs.forEach(function(input) {
        var timeout;
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                performLiveSearch(input);
            }, 300);
        });
    });
}

/**
 * تنفيذ البحث المباشر
 */
function performLiveSearch(input) {
    var searchTerm = input.value.toLowerCase();
    var targetTable = document.querySelector(input.getAttribute('data-target'));
    
    if (targetTable) {
        var rows = targetTable.querySelectorAll('tbody tr');
        rows.forEach(function(row) {
            var text = row.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
}

/**
 * تفعيل الرسوم المتحركة
 */
function initializeAnimations() {
    // إضافة رسوم متحركة للبطاقات
    var cards = document.querySelectorAll('.card');
    cards.forEach(function(card, index) {
        card.style.animationDelay = (index * 0.1) + 's';
        card.classList.add('fade-in');
    });
    
    // رسوم متحركة للأزرار
    var buttons = document.querySelectorAll('.btn');
    buttons.forEach(function(button) {
        button.addEventListener('click', function() {
            button.classList.add('btn-clicked');
            setTimeout(function() {
                button.classList.remove('btn-clicked');
            }, 200);
        });
    });
}

/**
 * عرض رسالة تأكيد
 */
function showConfirmDialog(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * عرض رسالة نجاح
 */
function showSuccessMessage(message) {
    showAlert(message, 'success');
}

/**
 * عرض رسالة خطأ
 */
function showErrorMessage(message) {
    showAlert(message, 'danger');
}

/**
 * عرض تنبيه
 */
function showAlert(message, type) {
    var alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    var container = document.querySelector('main .container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // إزالة التنبيه تلقائياً بعد 5 ثوان
        setTimeout(function() {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

/**
 * تحديث الوقت الحالي
 */
function updateCurrentTime() {
    var timeElements = document.querySelectorAll('.current-time');
    timeElements.forEach(function(element) {
        element.textContent = new Date().toLocaleString('ar-SY');
    });
}

// تحديث الوقت كل دقيقة
setInterval(updateCurrentTime, 60000);

/**
 * طباعة الصفحة
 */
function printPage() {
    window.print();
}

/**
 * تصدير البيانات
 */
function exportData(format, data) {
    if (format === 'csv') {
        exportToCSV(data);
    } else if (format === 'excel') {
        exportToExcel(data);
    }
}

/**
 * تصدير إلى CSV
 */
function exportToCSV(data) {
    var csv = convertToCSV(data);
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'export_' + new Date().getTime() + '.csv';
    link.click();
}

/**
 * تحويل البيانات إلى CSV
 */
function convertToCSV(data) {
    var csv = '';
    if (data.length > 0) {
        // إضافة العناوين
        csv += Object.keys(data[0]).join(',') + '\n';
        
        // إضافة البيانات
        data.forEach(function(row) {
            csv += Object.values(row).join(',') + '\n';
        });
    }
    return csv;
}

// تصدير الوظائف للاستخدام العام
window.SAMPro = {
    showConfirmDialog: showConfirmDialog,
    showSuccessMessage: showSuccessMessage,
    showErrorMessage: showErrorMessage,
    formatCurrency: formatCurrency,
    printPage: printPage,
    exportData: exportData
};
