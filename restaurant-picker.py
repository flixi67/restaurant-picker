from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    return print(
        "<h1>Restaurant Picker</h1>,
        "Here would go the description of the app and how to use it"
    )

@app.route('/preferences')
def restaurant():
    return render_template('inputs.html')

''' this is the simple post method for HTML forms we used in the lab to pass the inputs 
@app.route('/calculate', methods=['POST'])  # associating the POST method with this route
def calculate():

    # using the request method from flask to request the values that were sent to the server through the POST method
    value1 = request.form['value1']
    value2 = request.form['value2']
    operation = str(request.form['operation'])

    # convert the input to floating points
    value1 = float(value1)
    value2 = float(value2)

    if operation == 'addition':
        return render_template('calc.html', printed_result=str(value1 + value2))
    if operation == "substraction":
        return render_template('calc.html', printed_result=str(value1 - value2))
    if operation == "multiplication":
        return render_template('calc.html', printed_result=str(value1 * value2))
    if operation == "division":
        return render_template('calc.html', printed_result=str(value1 / value2))
    else:
        return render_template('calc.html', printed_result='Operation must be "addition"')
'''

if __name__ == '__main__':
    app.run(debug=True)