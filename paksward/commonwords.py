"""Common words, names and passwords the strength meter treats as guessable.

This is a modest built-in list, not a full dictionary. The meter assumes an attacker's dictionary is
much larger (about 10,000 words), so a word missing here is still charged as a word when it looks like
one. Adding words only makes the meter stricter.
"""

WORDS = frozenset("""
about above across action active actor adam admin after again agent ahead alarm album alert alex alice alive allow alone along alpha
always amazing amber angel anger angle animal annie answer apple april arch area army arrow art ashley asia atlas august aunt autumn
avenue baby back bacon badge bag baker ball banana band bank barbara barn base basket bath battery beach bean bear beauty bed bee beef
beer bell belt ben bench berry best beta bible bicycle big bike bill bird birth black blade blessing blind block blood blue board boat body
bomb bonus book boot boss bottle bottom bowl box boy brain brand brave bread break brick bridge bright brother brown brush bubble buddy
bug build bulb bull bunny burger bus business butter button buy cabin cable cake call camel camera camp canada candle candy cap car card
care carl carpet carrot case cash castle cat catch cave center chair chalk champion chance change charlie cheese chef cherry chess chicken
chief child chip chocolate chris church circle city class clean clear clever click cliff clock close cloud clown club coach coast coat code
coffee coin cold color comet computer cook cookie cool copper coral corn cotton cow crab crazy cream crew cricket crown crystal cup cute
daddy daisy dance danger daniel dark data date dave david day dead deal dear deep deer delta dennis desert desk devil diamond diary dinner
dirt dish doctor dog doll dollar dolphin domain door dot dragon draw dream dress drink drive drop drum duck dust eagle ear earth east easy
eat echo edge egg eight eleven email emily emma end energy engine enjoy eric even evening ever every evil exit eye face fact fairy faith fall
family fan fancy farm fast fat father fear feather fire first fish five flag flame flash flip floor flower fly food fool foot football forest
forever fox frank free fresh friday friend frog front fruit full fun funny future gabriel galaxy game garden gate gem george ghost giant gift
girl give glass globe glory goal goat god gold golf good google grace grape grass gray great green grey ground group guard guest guitar gun
hair half hammer hand happy harbor hard harry hat hate hawk head heart heaven heavy hello help henry hero hidden high hill history hockey
holiday home honey hope horse hospital hot hotel house hunter husband ice idea image india internet iron island jack jacob jacket james
jane january jason jazz jelly jennifer jesse jesus jewel job joe john joker jordan joy judge juice july jump june jungle junior just karen
kate keep kelly kevin key kick kid king kiss kitchen kitten knife knight know lady lake lamp land laptop large last laugh law lazy leader
leaf learn left lemon leo letter level life light lightning lily lime line lion lisa little live lizard lock logic lollipop lonely long look
lord lost love lovely lucky luna lunch machine madison magic mail major make man mango maple marble march margaret maria mark market mars
marvel mary master matrix matt max maybe meadow medal melon memory mercury metal michael michelle middle midnight mike milk million mind
mine mint mirror miss mission mobile model molly monday money monkey monster moon morning mother motor mountain mouse movie music mystery
name nancy nature navy neon nest net never new news nice nick night nine ninja noble noise north nose note nothing november number nurse
nut ocean october office oil old olive one open orange orbit order original oscar otter owl owner pace pack page paint pale panda paper
parent paris park party passion past patrick paul peace peach pearl pencil penguin pepper person pet peter phoenix phone photo piano pick
picture pie pig pilot pine pink pizza place planet plant plastic play player please plum pocket poem point poker police polo pool popcorn
power pretty prince princess prize pumpkin puppy purple puzzle queen quick quiet quiz rabbit race radio rain rainbow ranger rapid raven
reach read ready real red remember rich ride right ring river road robert robin robot rock rocket roll roman rome room rose round royal
ruby run russian sad safe sailor salad sally salmon salt sam sand santa sara sarah saturday save scarlet school science scooter score
scott sea season secret seven shadow shark sheep shell shield ship shirt shoe shop short show shy sierra silent silver simple sister six
sky sleep slow small smart smile smoke snake snow soccer soft solar soldier son song sophie soul sound soup south space spark speed spider
spirit sport spring square squirrel stand star start station steel stone storm story strange street strong student sugar summer sun sunday
sunny sunshine super surf swan sweet swim sword table tail tango tank taylor tea teacher team tech teddy ten tennis test thank thomas
thunder thursday tiger time tiny toast today tom tomato tomorrow tony tool top tower toy track train tree triangle tribe truck true trust
tuesday turtle twin two uncle under unicorn united universe up urban user valley vampire vanilla velvet venus victor video village
vincent violet virgin vision voice walk wall walnut warrior watch water wave way weather wednesday week welcome west whale wheel white
wild william willow wind window wine winner winter wish witch wolf woman wonder wood world worm yankee yard year yellow yes young zebra
zero zone zoo lagos abuja naija nigeria nigerian ibadan kano jollof blessing chinedu emeka ngozi chika tunde bola funke ade ola adebayo
password passwords login letmein welcome qwerty azerty asdf zxcv monkey dragon master shadow superman batman iloveyou trustno sunshine
princess football baseball whatever starwars computer freedom michael jordan hunter ranger buster thomas robert soccer harley
battery staple correct horse
""".split())

# The most common leaked passwords, in lowercase without trailing digits. A password that is one of
# these, with or without a few digits or symbols around it, is treated as already known to attackers.
TOP_PASSWORDS = frozenset("""
password passw0rd p4ssword pass pass123 admin administrator root toor login welcome letmein qwerty qwertyuiop qwerty123 azerty asdf asdfgh
asdfghjkl zxcvbn zxcvbnm iloveyou monkey dragon master shadow sunshine princess football baseball superman batman trustno1 starwars
freedom whatever hello hello123 abc abc123 abcd abcdef test testing guest changeme secret default google facebook love lovely blessing
jesus godisgood naija nigeria lagos 123456 12345 1234 123 111111 000000 654321 123123 121212 112233 11111111 12345678 123456789 1234567890
""".split())
