#codage de l'entête du message
#prend en argument le type du message, le numéro de séquence
"""
def coder_entete(tipe, num_sequence):

    #construction de deux octets comprenant le numéro de séquence et le type
    z = ( num_sequence << 6 ) + tipe 

    #taille de l'ensemble du message
    taille = len (data) + 4

    #on renvoie l'entête
    return(struct.pack( '!HH', taille , z ))
"""



#construction d'un acquittement
def acquittement(num):
    Type = 0b111111 #type acquittement 

    #construction de deux octets comprenant le numéro de séquence et le type
    z = ( num<<6 ) + Type 


    #taille de l'ensemble du message
    taille = 0b100

    #construction de la trame
    return(struct.pack( '!HH' , taille , z ))
