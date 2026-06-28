import aegisBrewing        from '../assets/beer_cards/Aegis Brewing beer.jpg';
import beerBigGlass        from '../assets/beer_cards/beer in big glass.jpg';
import beerFrostedMug      from '../assets/beer_cards/Beer in frosted mug.jpg';
import brightBeer          from '../assets/beer_cards/bright beer.jpg';
import budweiser           from '../assets/beer_cards/Budiveiser Beer.jpg';
import cherryTart          from '../assets/beer_cards/Cherry Tart.jpg';
import citrusBlast         from '../assets/beer_cards/Citrus Blast.jpg';
import coronaExtra         from '../assets/beer_cards/corona extra beer.jpg';
import crispMorning        from '../assets/beer_cards/Crisp morning.jpg';
import darkBeer            from '../assets/beer_cards/dark beer.jpg';
import flysianIPA          from '../assets/beer_cards/FLYSIAN daygloa IPA.jpg';
import foamyBeer           from '../assets/beer_cards/foamy beer.jpg';
import galacticStout       from '../assets/beer_cards/Galactic Stout.jpg';
import goldenHour          from '../assets/beer_cards/Golden Hour.jpg';
import guinnessStout       from '../assets/beer_cards/GUINNESS draught staout beer.jpg';
import hazyHorizon         from '../assets/beer_cards/Hazy Horizon.jpg';
import heineken            from '../assets/beer_cards/Heineken beer.jpg';
import lowGlassBeer        from '../assets/beer_cards/low glass beer.jpg';
import mediumColorBeer     from '../assets/beer_cards/meduim color beer tall glass.jpg';
import mediumRoastBeer     from '../assets/beer_cards/meduim roast beer.jpg';
import midnightPorter      from '../assets/beer_cards/Midnight Porter.jpg';
import millerLite          from '../assets/beer_cards/miller lite beer can.jpg';
import modelo              from '../assets/beer_cards/Modelo beer.jpg';
import rubyRed             from '../assets/beer_cards/Ruby Red.jpg';
import sourAle             from '../assets/beer_cards/Sour Ale.jpg';
import spicedPumpkin       from '../assets/beer_cards/Spiced Pumpkin.jpg';
import troges              from '../assets/beer_cards/TROGES beer.jpg';

// Ordered list of [keyword, image] — first substring match wins (case-insensitive).
const STYLE_MAP = [
  // Imperial / Russian Imperial Stout (must come before plain "stout")
  ['imperial stout',   galacticStout],
  ['russian imperial', galacticStout],
  // Stout / Porter / Dark
  ['stout',            guinnessStout],
  ['porter',           midnightPorter],
  ['schwarzbier',      darkBeer],
  ['dark lager',       darkBeer],
  ['dark ale',         darkBeer],
  ['smoked',           darkBeer],
  ['rauch',            darkBeer],
  // Hazy / NEIPA (must come before plain "ipa")
  ['new england',      hazyHorizon],
  ['neipa',            hazyHorizon],
  ['hazy',             hazyHorizon],
  // IPA / Hoppy
  ['ipa',              flysianIPA],
  // Pale Ale
  ['pale ale',         citrusBlast],
  ['session',          brightBeer],
  // Wheat / Hefeweizen
  ['hefeweizen',       foamyBeer],
  ['weizen',           foamyBeer],
  ['witbier',          foamyBeer],
  ['wheat',            foamyBeer],
  // Sour / Wild / Lambic
  ['lambic',           sourAle],
  ['gueuze',           sourAle],
  ['berliner',         sourAle],
  ['gose',             sourAle],
  ['wild ale',         sourAle],
  ['sour',             sourAle],
  // Fruit / Specialty
  ['fruit',            cherryTart],
  ['cherry',           cherryTart],
  ['cider',            cherryTart],
  ['mead',             cherryTart],
  ['perry',            cherryTart],
  // Belgian / Saison / Farmhouse
  ['saison',           goldenHour],
  ['farmhouse',        goldenHour],
  ['dubbel',           goldenHour],
  ['tripel',           goldenHour],
  ['quadrupel',        goldenHour],
  ['belgian',          goldenHour],
  // Seasonal / Specialty
  ['pumpkin',          spicedPumpkin],
  ['winter',           spicedPumpkin],
  ['spiced',           spicedPumpkin],
  ['seasonal',         spicedPumpkin],
  // Amber / Red
  ['amber',            rubyRed],
  ['red ale',          rubyRed],
  ['irish',            rubyRed],
  // Brown / Alt / Rye
  ['brown ale',        mediumRoastBeer],
  ['altbier',          mediumRoastBeer],
  ['rye',              mediumRoastBeer],
  // Bock / Märzen / Oktoberfest / Scottish
  ['bock',             mediumColorBeer],
  ['märzen',           mediumColorBeer],
  ['marzen',           mediumColorBeer],
  ['oktoberfest',      mediumColorBeer],
  ['scottish',         mediumColorBeer],
  ['scotch ale',       mediumColorBeer],
  // Barleywine / Old Ale / Strong
  ['barleywine',       aegisBrewing],
  ['barley wine',      aegisBrewing],
  ['old ale',          aegisBrewing],
  ['strong ale',       aegisBrewing],
  // Vienna / Mexican Lager
  ['vienna',           modelo],
  ['mexican lager',    modelo],
  // Pilsner / Helles
  ['pilsener',         heineken],
  ['pilsner',          heineken],
  ['helles',           heineken],
  // Light / Low-alcohol
  ['light beer',       millerLite],
  ['low alcohol',      millerLite],
  // Generic Lager
  ['lager',            coronaExtra],
  // Blonde / Cream Ale
  ['blonde',           crispMorning],
  ['blond',            crispMorning],
  ['cream ale',        crispMorning],
  // Golden / Bright
  ['golden',           brightBeer],
];

// Generic pool used when no style keyword matches.
// beer_id % pool.length picks deterministically — same ID always maps to same image.
const FALLBACK_POOL = [beerBigGlass, beerFrostedMug, troges, lowGlassBeer, budweiser];

function hashId(id) {
  let h = 5381;
  const s = String(id);
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h) ^ s.charCodeAt(i);
  return Math.abs(h);
}

export function getBeerImage(style, id) {
  const s = (style || '').toLowerCase();
  for (const [keyword, img] of STYLE_MAP) {
    if (s.includes(keyword)) return img;
  }
  const n = parseInt(id, 10);
  return FALLBACK_POOL[(isNaN(n) ? hashId(id) : n) % FALLBACK_POOL.length];
}

export const DEFAULT_BEER_IMAGE = beerBigGlass;
