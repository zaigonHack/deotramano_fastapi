import smtplib, ssl

host = "ssl0.ovh.net"
port = 587
user = "servinfo@deotramano.com"
password = "17112502@dD"   # ⚠️ tu contraseña real de OVH

with smtplib.SMTP(host, port) as server:
    server.starttls(context=ssl.create_default_context())
    server.login(user, password)
    server.sendmail(
        user,
        "servinfo@deotramano.com",  # <-- cámbialo por uno tuyo para probar
        "Subject: Test\n\nHola desde OVH SMTP!"
    )
print("Correo enviado 🚀")
