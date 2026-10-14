"""Fictional citizen-science reports and the labels the classifier must produce.

Thirty-six short reports sent to the made-up "Marshline Nature Watch" app. Each is
labelled with one of six routing groups. Some are deliberately tricky: a
seahorse is a fish, a bat is a mammal, a newt is an amphibian, a whale-shaped
cloud is not a sighting at all. House rule: any animal met in the open sea (seals,
porpoises, a turtle) is marine_life; seabirds on land are birds.
"""

LABELS = [
    "birds",
    "mammals",
    "reptiles_amphibians",
    "insects",
    "marine_life",
    "not_a_sighting",
]

# (report text, correct label)
REPORTS: list[tuple[str, str]] = [
    # birds
    ("Heron standing motionless in the reed bed behind the car park, 7am, grey with a long yellow bill.", "birds"),
    ("Small flock of about 30 starlings wheeling over the allotments at dusk.", "birds"),
    ("Something with a bright red cap hammering on the oak outside my kitchen window.", "birds"),
    ("A barn owl floated along the hedge row last night, completely silent, pale underneath.", "birds"),
    ("Kingfisher flash of electric blue under the footbridge, gone before I could get my phone out.", "birds"),
    ("Puffins lined up on the cliff ledge at the headland, bills full of sand eels.", "birds"),
    # mammals
    ("Fox trotting across the cricket pitch at 6am, bushy tail, totally unbothered by me.", "mammals"),
    ("Two roe deer grazing at the woodland edge near the north gate.", "mammals"),
    ("Pipistrelle bats swooping over the canal as it got dark, at least five of them.", "mammals"),
    ("Hedgehog snuffling along the garden fence, curled up when my torch hit it.", "mammals"),
    ("Water vole plop into the ditch as I walked past, saw its blunt round nose.", "mammals"),
    ("Otter slid into the river by the mill, long rudder tail, sleek whiskered head.", "mammals"),
    # reptiles / amphibians
    ("Adder basking on the sandy path near the heath, zigzag pattern down its back.", "reptiles_amphibians"),
    ("Dozens of tiny toadlets crossing the lane after last night's rain.", "reptiles_amphibians"),
    ("Slow worm under the compost sheet, shiny and copper coloured, no legs.", "reptiles_amphibians"),
    ("Great crested newt in the pond net during the school pond-dipping session, orange belly.", "reptiles_amphibians"),
    ("A common lizard sunning itself on the log pile by the shed.", "reptiles_amphibians"),
    ("Grass snake swimming across the village pond with its head held high.", "reptiles_amphibians"),
    # insects
    ("Huge dragonfly patrolling the pond, metallic blue-green body, hovered right by my face.", "insects"),
    ("Cluster of ladybird larvae on my nettles, spiky and black with orange dots.", "insects"),
    ("Stag beetle crawling across the patio at dusk, antlers and all.", "insects"),
    ("Painted lady butterflies all over the buddleia this afternoon, easily a dozen.", "insects"),
    ("Bumblebee nest in the old bird box, constant traffic in and out.", "insects"),
    ("Swarm of mayflies dancing over the river just after sunset.", "insects"),
    # marine life
    ("Grey seal hauled out on the sandbank at low tide, pup beside it.", "marine_life"),
    ("Moon jellyfish washed up along the whole length of the beach this morning.", "marine_life"),
    ("A seahorse clinging to the eelgrass while snorkelling at the cove.", "marine_life"),
    ("Pod of harbour porpoises rolling past the headland, four or five animals.", "marine_life"),
    ("Hermit crab in a rock pool using a tiny whelk shell, waved its claws at me.", "marine_life"),
    ("A loggerhead turtle surfaced beside our boat, two miles out at sea.", "marine_life"),
    # not a sighting
    ("How do I change the email address on my Nature Watch account?", "not_a_sighting"),
    ("Cloud over the estuary looked exactly like a whale, honestly amazing shape.", "not_a_sighting"),
    ("The plastic duck in the fountain has gone missing again, can the council replace it?", "not_a_sighting"),
    ("Thanks for the lovely newsletter, the photo competition results were brilliant.", "not_a_sighting"),
    ("Is the nature reserve car park open on bank holidays? Planning a walk.", "not_a_sighting"),
    ("Found a sticker of a hummingbird on the pavement, who do I ask to get it removed?", "not_a_sighting"),
]
