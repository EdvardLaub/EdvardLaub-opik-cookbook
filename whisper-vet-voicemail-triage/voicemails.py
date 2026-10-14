"""Five fictional overnight voicemails for Willowbrook Animal Clinic.

Everything here is invented: the callers, the pets, the phone numbers (555
numbers). Each script is spoken by OpenAI TTS at run time, so the clinic's
"answering machine" is synthetic and nothing audio is committed. `expected`
is the urgency a vet nurse would assign; the app never shows it to the model,
only the test suite uses it.
"""

VOICEMAILS = [
    {
        "id": "vm1-xylitol",
        "voice": "nova",
        "received": "11:42 pm",
        "expected": "emergency",
        "script": (
            "Hi, this is Marta Okafor, my dog Biscuit, he's a beagle, he just "
            "got into my handbag and ate most of a pack of sugar free gum. "
            "I checked the label and it says xylitol. He's drooling a lot and "
            "he seems wobbly. Please call me back right away, my number is "
            "five five five, zero one four two."
        ),
    },
    {
        "id": "vm2-blocked-cat",
        "voice": "onyx",
        "received": "1:15 am",
        "expected": "emergency",
        "script": (
            "Hello, it's Dev Raman. My cat Pepper, he's a neutered male, has "
            "been going back and forth to the litter box for hours and nothing "
            "comes out. He's crying and he keeps licking himself. I read that "
            "this can be deadly in male cats. Call me on five five five, "
            "zero one seven seven, as soon as you hear this."
        ),
    },
    {
        "id": "vm3-rabbit-appetite",
        "voice": "shimmer",
        "received": "6:50 am",
        "expected": "same-day",
        "script": (
            "Good morning, this is Joanna Lindqvist. My rabbit Clover hasn't "
            "touched her hay or pellets since yesterday evening. She's still "
            "drinking a little and she's sitting up, but her droppings are "
            "tiny. Could someone fit her in today? You can reach me on five "
            "five five, zero one nine three."
        ),
    },
    {
        "id": "vm4-puppy-limp",
        "voice": "echo",
        "received": "7:30 am",
        "expected": "same-day",
        "script": (
            "Hi, Tomasz Kowal here. My puppy Juno has been limping on her "
            "back left leg for two days now. She still plays and eats fine, "
            "but she cries when I touch her knee. I'd like to bring her in "
            "today if there's a slot. Five five five, zero one two eight."
        ),
    },
    {
        "id": "vm5-refill",
        "voice": "fable",
        "received": "8:05 am",
        "expected": "routine",
        "script": (
            "Hello, this is Grace Whitfield calling about my greyhound Otis. "
            "He's due for his monthly heartworm tablets and I'd like to pick "
            "up a refill sometime this week. No rush at all. My number is "
            "five five five, zero one six six. Thank you."
        ),
    },
]
