"""Words for passphrases. About 190 words is small, so each word adds ~7.6 bits.
The generator reports entropy from the real list size and picks 7 words by default.
A larger list (such as the 7,776-word EFF list) can replace this later with no other change."""

_RAW = """acorn amber anchor apple arrow atlas badge basil beach bench berry birch blaze bloom bonus brave bread brick brook
cabin cable camel candy canoe cargo cedar chair chalk charm cherry chess cider cliff clock cloud clover coast cobra coral cotton
crane crown daisy delta denim diver dolphin dragon dream eagle earth echo elder ember fable falcon fern ferry field flame flint
forest fossil fox frost galaxy garden garlic ginger glacier globe grape gravel harbor hazel heron honey horizon island ivory
jacket jade jelly jungle kayak kettle kiwi koala lagoon lantern lemon lilac lotus lunar magnet mango maple marble meadow melon
mirror mist mocha moss nectar noble nutmeg oasis olive onyx orbit orchid otter oyster paddle panda pearl pepper pine planet plum
pocket prism pumpkin quartz quill rabbit radar raven reef ribbon river robin rocket saddle sage sailor salmon sand scarlet shadow
silver sketch sky slate sparrow spice spruce summit sunset swan thistle thunder tiger timber topaz tulip tundra umber valley
velvet violet walnut willow window winter wolf yarrow yonder zebra zephyr"""

WORDS = tuple(dict.fromkeys(_RAW.split()))
