import random


def selectionSort(liste_us):
    n = len(liste_us)
    for i in range(n):
        kleinstezahl = i
        for j in range(i + 1, n):
            if liste_us[j] < liste_us[kleinstezahl]:
                kleinstezahl = j
        liste_us[i], liste_us[kleinstezahl] = liste_us[kleinstezahl], liste_us[i]
    return liste_us


# Hauptprogamm ##############
Zufallsliste = random.sample(range(1, 39), 10)
print("Unsortierte Liste:", Zufallsliste)
sortierte_liste = selectionSort(Zufallsliste)
print("Sortierte Liste:", sortierte_liste)
