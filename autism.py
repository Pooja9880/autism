import time
import speech_recognition as sr
import pyttsx3
import cv2
from keras.models import load_model
import numpy as np
import pandas as pd
import random
import inflect
import serial

# Load pre-trained models
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
emotion_model = load_model('C:/Users/Admin/OneDrive/Desktop/autism2/emotion_model_updated.h5', compile=False)
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

# Initialize Text-to-Speech engine with a slower rate
engine = pyttsx3.init()
rate = engine.getProperty('rate')
engine.setProperty('rate', rate - 50)  # Decrease the rate by 50 (adjust as needed)

# Initialize Serial connection with Arduino
# Replace '/dev/ttyUSB0' with the appropriate port for your Arduino
arduino_port = 'COM5'
arduino_baudrate = 9600
arduino = serial.Serial(arduino_port, arduino_baudrate)
time.sleep(2)  # Wait for Arduino to initialize


def send_command_to_arduino(command):
    arduino.write(command.encode())
    time.sleep(1)  # Wait for Arduino to process the command


# Initialize Excel data frame
columns = ['Timestamp', 'Detected Emotion', 'Question', 'User Response', 'Activity']
df = pd.DataFrame(columns=columns)


def speak(text):
    engine.say(text)
    engine.runAndWait()


def detect_emotion(face_roi):
    face_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    face_roi = cv2.resize(face_roi, (48, 48))
    face_roi = face_roi.astype('float') / 255.0
    face_roi = np.expand_dims(face_roi, axis=-1)  # Keep only one channel

    face_roi = np.repeat(face_roi, 3, axis=-1)
    face_roi = np.expand_dims(face_roi, axis=0)  # Add a batch dimension

    predicted_emotion = emotion_model.predict(face_roi)[0]
    emotion_label = emotion_labels[np.argmax(predicted_emotion)]
    confidence = max(predicted_emotion)

    return emotion_label, confidence

def display_emotion_indicator(emotion):
    # Implement the logic to display the emotion indicator, e.g., emoji or visual effect
    print(f"Displaying emotion indicator for {emotion}")
    
    
def recognize_speech():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("Say something:")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        print("Recognizing...")
        user_response = recognizer.recognize_google(audio)
        print(f"User's response: {user_response}")
        return user_response
    except sr.UnknownValueError:
        print("Sorry, I couldn't understand what you said.")
        return ""
    except sr.RequestError as e:
        print(f"Error connecting to Google API: {e}")
        return ""


def update_excel(timestamp, detected_emotion, question, user_response, activity):
    global df
    new_data = {'Timestamp': timestamp, 'Detected Emotion': detected_emotion,
                'Question': question, 'User Response': user_response, 'Activity': activity}
    df = df.append(new_data, ignore_index=True)
    df.to_excel('conversation_with_kid.xlsx', index=False)
    print(f"Updating Excel: Timestamp={timestamp}, Emotion={detected_emotion}, "
          f"Question={question}, Response={user_response}, Activity={activity}")


def detect_emotion_for_n_seconds(n_seconds):
    cap = cv2.VideoCapture(0)
    start_time = time.time()
    detected_emotion = None

    while time.time() - start_time < n_seconds:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        max_confidence = 0

        for (x, y, w, h) in faces:
            face_roi = frame[y:y + h, x:x + w]

            current_emotion, confidence = detect_emotion(face_roi)

            if confidence > 0.5 and confidence > max_confidence:
                detected_emotion = current_emotion
                max_confidence = confidence

            text = f'{current_emotion} ({confidence:.2f})'
            cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.imshow('Frame', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    return detected_emotion


def ask_name():
    send_command_to_arduino("say_hil")  # Send command to Arduino
    speak("Hi there! I'm Obo, your friendly companion. What's your name?")

    user_response = recognize_speech()
    print(f"User's response: {user_response}")

    name_keywords = ["my name is", "I'm", "I am", "myself"]
    for keyword in name_keywords:
        if keyword in user_response.lower():
            user_response = user_response.lower().replace(keyword, "").strip()
            break

    detected_emotion = detect_emotion_for_n_seconds(5)

    if detected_emotion in ["happy", "surprised"]:
        speak("You seem happy! Is there a special reason? Did something exciting happen today?")
    elif detected_emotion in ["scared", "angry"]:
        speak("Don't be scared! I'm just a friendly robot, and I won't harm you.")
    elif detected_emotion == "sad":
        speak("Hey there! What happened? If you want, I can tell you a joke to cheer you up.")
        tell_joke()
    elif detected_emotion == "neutral":
        speak("Hmm, you look calm and neutral. How am I looking?")

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    update_excel(timestamp, detected_emotion, "What's your name?", user_response, "Introduction")

    speak(f"Nice to meet you, {user_response}!")


def tell_joke():
    jokes = [
        "Why did the computer take up gardening? Because it wanted to improve its root system!",
        "How does a computer get drunk? It takes screenshots!",
        "Why did the robot bring a ladder to the bar? Because it heard the drinks were on the house!",
        "What do you call a robot that always tells jokes? A pun-dit!",
        "Why did the robot go to school? To get a little brighter!"
    ]
    speak("Here's a joke for you: " + random.choice(jokes))


def general():
    send_command_to_arduino("shake_hand")  # Send command to Arduino
    session_start_time = time.strftime('%Y-%m-%d %H:%M:%S')

    def ask_and_update(question, activity):
        speak(question)  # Use a child-friendly voice or sound effects

        # Detect emotion with a visual indicator (e.g., emoji)
        detected_emotion = detect_emotion_for_n_seconds(5)
        display_emotion_indicator(detected_emotion)

        user_response = recognize_speech()
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        update_excel(timestamp, detected_emotion, question, user_response, activity)

    # Introduce yourself with excitement and animation
    speak("Hey there!  I'm super excited to meet you!  Let's dive into some fun questions to get to know each other better!")

    # Use playful language and visuals for each question
    ask_and_update("tell me your father's name", "Introduction")
    ask_and_update("tell me your mother's name", "Introduction")
    # ask_and_update("Who's your bestie for life, the one you always have a blast with? ", "Introduction")
    # ask_and_update(f"wow  that's awesome!", "Introduction")
    # ask_and_update("So, which school are you currently studying in?", "Introduction")
    # ask_and_update(f"Nice! And which standard are you in at ?", "Introduction")
    # ask_and_update("Cool! Do you have a favorite subject?", "Introduction")
    # ask_and_update(f"Why do you like the subject? What do you find interesting about it?", "Introduction")
    ask_and_update("Nice choice! Now, what's your favorite color?", "Introduction")
    ask_and_update("Interesting! How about your favorite animal?", "Introduction")
    ask_and_update("Cool! Lastly, what's your favorite game?", "Introduction")

    # Wrap up with a positive and playful closing
    speak("Wow, you're super cool!  I had a blast getting to know you.  Let's hang out again soon for more fun!")


def ordinal(number):
    p = inflect.engine()
    return p.ordinal(number)


def ask_clapping():
    send_command_to_arduino("shake_hand")
    speak("Let's clap !!!!....")  # Use a playful voice
    user_response = recognize_speech()

    # Emotion detection before counting
    detected_emotion_before = detect_emotion_for_n_seconds(5)
    # Perform the clapping
    perform_clapping(3)

    speak("Great job! You're a champion!")

    # Emotion detection after counting
    detected_emotion_after = detect_emotion_for_n_seconds(5)

    # Update Excel log with counting information, user response, and emotions
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    update_excel(timestamp, detected_emotion_before, "Counting", user_response, "Counting")


def perform_clapping(clap_count):
    speak("Let's start clapping!")
    send_command_to_arduino("clap")
    for _ in range(clap_count):
        print("*clap*")
        time.sleep(1)


def sing_interactive_rhyme():
    send_command_to_arduino("clap")  # Send command to Arduino
    nursery_rhymes = {
        "twinkle": """
            Twinkle, twinkle, little star,
            How I wonder what you are!
            Up above the world so high,
            Like a diamond in the sky.
            Twinkle, twinkle, little star,
            How I wonder what you are!
        """,
        "jack and jill": """
            Jack and Jill went up the hill,
            To fetch a pail of water.
            Jack fell down and broke his crown,
            And Jill came tumbling after.
        """,
        "humpty dumpty": """
            Humpty Dumpty sat on a wall,
            Humpty Dumpty had a great fall.
            All the king's horses and all the king's men,
            Couldn't put Humpty together again.
        """,
        "itsy bitsy spider": """
            The itsy bitsy spider climbed up the water spout,
            Down came the rain and washed the spider out.
            Out came the sun and dried up all the rain,
            And the itsy bitsy spider climbed up the spout again.
        """
    }

    speak("I can sing different nursery rhymes. Would you like to hear Twinkle, Jack and Jill, Humpty Dumpty, or Itsy Bitsy Spider?")

    user_response = recognize_speech().lower()

    playful_responses = [
        "Great choice!",
        "You're in for a treat!",
        "Let's dive into the world of nursery rhymes!",
        "Get ready for some fun!",
    ]
    playful_response = random.choice(playful_responses)
    speak(playful_response)

    if user_response in nursery_rhymes:
        detected_emotion = detect_emotion_for_n_seconds(5)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        update_excel(timestamp, detected_emotion, "Sing Rhymes", user_response, "Singing Rhyme")
        speak(nursery_rhymes[user_response])
    else:
        speak("I'm sorry, I didn't catch that. Let's sing Twinkle, Twinkle, Little Star.")
        detected_emotion = detect_emotion_for_n_seconds(5)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        update_excel(timestamp, detected_emotion, "Sing Rhymes", "Twinkle", "Singing Rhyme")
        speak(nursery_rhymes["twinkle"])


def ask_counting():
    session_start_time = time.strftime('%Y-%m-%d %H:%M:%S')
    detected_emotion = detect_emotion_for_n_seconds(5)
    display_emotion_indicator(detected_emotion)
    
    speak("Let's have some counting fun! I'll say a number, and you repeat after me.")
    send_command_to_arduino("count")  # Send command to Arduino
    for i in range(1, 10):
        speak(str(i))
        time.sleep(1)

    user_response = "User counted from 1 to 9."
    update_excel(time.strftime('%Y-%m-%d %H:%M:%S'), detected_emotion, "Counting", user_response, "Counting")
    
def color_practice():
    colors = ['red', 'green', 'white', 'yellow']
    score = 0
    
    speak("Let's play the color guessing game!")
    
    for color in colors:
        # Send lowercase command to Arduino
        send_command_to_arduino(color)
        
        # Check emotion
        try:
            detected_emotion = detect_emotion_for_n_seconds(5)
        except Exception as e:
            print(f"Error detecting emotion: {e}")
            detected_emotion = None
        
        display_emotion_indicator(detected_emotion)
        
        # Speak the color
        speak(f"What color do you see?")
        
        # Recognize user response
        user_response = recognize_speech().lower()
        
        # Validate user response
        if user_response.strip() == "":
            speak("Sorry, I couldn't understand you. Please try again.")
            continue  # Skip to the next iteration
            
        print(f"User response: {user_response}, Expected color: {color}")
        
        # Evaluate user response
        if user_response == color:
            speak("Wow, good job! You guessed it right! Now your score is " + str(score + 1))
            score += 1
            send_command_to_arduino("clap")
        else:
            speak(f"Sorry, the color is {color}.")
        
        # Append data to Excel
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        update_excel(timestamp, detected_emotion, f"Guess Color - {color.capitalize()}", user_response, "Color Guessing")
        
        if score == 4:
            speak("Congratulations, you're a champion!")
            break
        elif score == 3:
            speak("Great job! Keep it up.")
        elif score == 1:
            speak("Nice try.")
        
        speak("Now guess the next color.")
    
    if score < 4:
        speak("Better luck next time!")

def end_conversation():
    send_command_to_arduino("say_hil")
    speak("It was great chatting with you! If you ever want to talk again, I'll be here. Take care and bye! have a nice day champ!!.....")


if __name__ == "__main__":
    #ask_name()
    #general()
    #ask_counting()
    #sing_interactive_rhyme()
    #ask_clapping()
    #ask_counting()
    color_practice()
    #end_conversation()
