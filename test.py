from flask import Flask, render_template, request

def func1(i):
    print("func1: " + str(i))


app = Flask(__name__)
app.secret_key = b'notSoSecret'
@app.route('/', methods = ['GET', 'POST'])
def index():
    if request.method == 'POST':
        if request.form.get('action1') == 'VALUE1':
            text = request.form.get('textbox')
            func1(1)

            pass
        elif request.form.get('action2') == 'VALUE2':
            func1(2)

            pass
        else:
            pass
    elif request.method == 'GET':
        return render_template('index.html')

    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True, port = 8080, host ='192.168.36.30')
