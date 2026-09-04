@app.get("/")
def home():
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>My Jarvis</title>
</head>
<body>

<h1>🤖 Jarvis</h1>

</body>
</html>
""")
