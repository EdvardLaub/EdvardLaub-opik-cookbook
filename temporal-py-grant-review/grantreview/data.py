"""Fictional data for the (made-up) Larkfield Neighbourhood Foundation."""

from grantreview.models import Application

FOUNDATION = "Larkfield Neighbourhood Foundation"
MAX_GRANT = 5_000
PASS_MARK = 10  # out of 15; at or above this the panel approves
LARKFIELD_PREFIXES = ("LK1", "LK2", "LK3", "LK4")

# What the (stubbed) charity register says about each applicant.
REGISTER = {
    "Orchard Row Residents' Association": "registered",
    "Tidemill Youth Football Club": "registered",
    "Brightwater Pop-Up Gallery Ltd": "dissolved",
}

APPLICATIONS = [
    Application(
        id="GR-2041",
        applicant="Orchard Row Residents' Association",
        postcode="LK2 4QT",
        amount_requested=3_200,
        title="Community orchard and tool shed",
        summary=(
            "We want to turn the derelict plot behind Orchard Row into a shared fruit garden. "
            "Funds cover 24 heritage apple and pear saplings, raised beds, and a lockable shed "
            "for tools. Eleven households have already signed up to a watering rota and the "
            "council has agreed a five-year licence on the land. We will hold two open "
            "planting days with the primary school."
        ),
    ),
    Application(
        id="GR-2042",
        applicant="Tidemill Youth Football Club",
        postcode="LK3 1AB",
        amount_requested=4_800,
        title="New floodlights for the training pitch",
        summary=(
            "Our under-14s cannot train after 4pm in winter. We would like floodlights for the "
            "pitch. We have not yet asked the landlord, obtained quotes, or checked whether "
            "planning permission is needed. Probably it will cost about what we are asking."
        ),
    ),
    Application(
        id="GR-2043",
        applicant="Brightwater Pop-Up Gallery Ltd",
        postcode="LK2 9ZZ",
        amount_requested=2_500,
        title="Summer street art trail",
        summary="A trail of ten murals on shopfronts along Brightwater Road, with a printed map.",
    ),
]
