# -*- coding: utf-8 -*-
from twisted.internet.protocol import DatagramProtocol
from c2w.main.lossy_transport import LossyTransport
import logging
import struct
import ipaddress
import c2w
from c2w.main.constants import ROOM_IDS
logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.udp_chat_server_protocol')
from twisted.internet import reactor

#gestion de la file d'attente des message
#on enlève le message qui vient d'être envoyé
def messageSent(file):
    file.pop(0)
    return

#ajout d'un message à la file d'attente
def messageToSend(file, message):
    file.append(message)
    return



class c2wUdpChatServerProtocol(DatagramProtocol):

    def __init__(self, serverProxy, lossPr):
        """
        :param serverProxy: The serverProxy, which the protocol must use
            to interact with the user and movie store (i.e., the list of users
            and movies) in the server.
        :param lossPr: The packet loss probability for outgoing packets.  Do
            not modify this value!

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attribute:

        .. attribute:: serverProxy

            The serverProxy, which the protocol must use
            to interact with the user and movie store in the server.

        .. attribute:: lossPr

            The packet loss probability for outgoing packets.  Do
            not modify this value!  (It is used by startProtocol.)

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
        """
        #: The serverProxy, which the protocol must use
        #: to interact with the server (to access the movie list and to 
        #: access and modify the user list).
        self.serverProxy = serverProxy
        self.lossPr = lossPr
        #self.numeroSequence = 0
        self.userList = []
        self.filmList = []
        self.dictionnary = {}
        self.host_port = ('0', 0)
        self.nbrAckRecu = 0 
    
    class fiabiliteClient():
        def __init__(self, userName, room, host_port):
            self.hostPort = host_port
            self.userName = userName
            self.chatRoom = room
            self.numeroSequence = 0
            self.numeroSequenceAttendu = 1
            self.counter = 0
            self.timer = None
            self.etatAck = 1
            self.nextNumSeq = 1
            self.file = []
      


    def startProtocol(self):
        """
        DO NOT MODIFY THE FIRST TWO LINES OF THIS METHOD!!

        If in doubt, do not add anything to this method.  Just ignore it.
        It is used to randomly drop outgoing packets if the -l
        command line option is used.
        """
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport

    def datagramReceived(self, datagram, host_port):
        """
        :param string datagram: the payload of the UDP packet.
        :param host_port: a touple containing the source IP address and port.
        
        Twisted calls this method when the server has received a UDP
        packet.  You cannot change the signature of this method.
        """    
        #self.host_port= host_port
        
        #decomposition de la trame
        reste=struct.unpack('!H', datagram[2:4])[0] #deux octets contenant le numero de seq et le type
        longueur=struct.unpack('!H', datagram[:2])[0] #recuperation des 2 premiers octets
        data = struct.unpack(str(longueur-4)+'s', datagram[4:])[0] #recuperation du payload
        num = (reste & 0b1111111111000000) >> 6
        tipe = (reste & 0b0000000000111111)
        print("\t\t\ttype {} data {} seq {}".format(tipe, data, num))
        
        
        if tipe ==63:
            self.ackRecu(self.dictionnary[host_port].hostPort, num)
        
        
        #Reception d'une requete d'inscription d'inscription
        if (tipe==0b000001) :
            self.dictionnary[host_port] = self.fiabiliteClient(None, None, host_port)
            if self.dictionnary[host_port].numeroSequenceAttendu == num :                
                self.nbrAckRecu = 0
                print('nbr ack recu', self.nbrAckRecu)
                #envoi d'un acquittement pour la requete d'inscription
                ty = 0b111111
                #construction de deux octets comprenant le numéro de séquence et le type
                x = ( num << 6 ) + ty
                taille = 0b100
                ack = struct.pack( '!HH', taille , x)

                print('acquittement prêt à envoyer')
                self.transport.write(ack, host_port)
                self.dictionnary[host_port].numeroSequenceAttendu += 1

 
            #verification de la requete d'inscription
            #on récuère la liste des utilisateurs : initialement elle est vide
            self.userList = self.serverProxy.getUserList()
            print('liste utilisateur', self.userList)
            username=data.decode("utf-8")

            erreur = 0
            for i in range(0, len(self.userList)-1) : 
                #verification de l'unicité du login
                if(self.userList[i]==username) : 
                    erreur = 0b00000001
            #login trop long        
            if (len(data)>254): 
                erreur = 0b00000010
            #login contenant un espace
            is_space = ' ' in username
            if is_space == True:
                erreur = 0b00000011
            print('l erreur est' + str(erreur))
            #la demande de connection est valable 
            if erreur == 0:
                self.dictionnary[host_port].numeroSequence += 1
                z = (self.dictionnary[host_port].numeroSequence << 6) + 0b000111
                taille = 0b100

                buf = bytearray(taille)
                struct.pack_into( '!HH' ,buf,0, taille , z)
                self.processEnvoi(buf, host_port)

                #on ajoute l'utilisateur à la liste
                print(username)
                print(host_port)
                self.serverProxy.addUser(username, ROOM_IDS.MAIN_ROOM, host_port)
                
                self.dictionnary[host_port].userName = username
                self.dictionnary[host_port].chatRoom = ROOM_IDS.MAIN_ROOM
                self.userList = self.serverProxy.getUserList()
                userRoom=self.dictionnary[host_port].chatRoom

                print('liste utilisateur', self.userList)
                print('dictionary', self.dictionnary)
                print(userRoom)
                

            #la demande de connection n'est pas valable
            else:                               
                #contruction du message d'erreur
                self.dictionnary[host_port].numeroSequence += 1
                Type = 0b001000
                z = ( self.dictionnary[host_port].numeroSequence << 6 ) + Type 
                taille = 0b101
                buf = bytearray(taille)
                struct.pack_into( '!HHB' ,buf,0, taille , z, erreur)
                self.processEnvoi(buf, host_port)

        
        
        #envoi de la liste des films après reception de l'ack de inscription_ok
        if (tipe == 63 and num == 1) : 
            #envoie de la liste de film
            print(num)
            print(self.dictionnary[host_port].numeroSequence)
            if self.dictionnary[host_port].numeroSequence == num : 
                self.dictionnary[host_port].numeroSequence += 1
                z = (self.dictionnary[host_port].numeroSequence << 6) + 0b000010
                taille_msg_entier =0
                payload = b''
                print('on parcourt la liste des films')
                
                for m in self.serverProxy.getMovieList():
                    print("Movie title :", m.movieTitle)
                    print("IP Salon :", m.movieIpAddress)
                    ip= m.movieIpAddress.split(".")                               
                    print("le port:", m.moviePort)
                    print("identifiant:", m.movieId)
                    data = m.movieTitle.encode("utf-8")
                    taille = len(data)
                    taille_msg_entier = taille_msg_entier + taille + 8
                    liste=struct.pack('!BBBBBHB' + str(taille) +'s' , taille+8, int(ip[0]), int(ip[1]), int(ip[2]), int(ip[3]), m.moviePort, m.movieId, data)
      
 
                    payload = payload + liste
                buf = bytearray(taille_msg_entier + 4)
                struct.pack_into('!HH' + str(taille_msg_entier) + 's',buf,0, taille_msg_entier + 4, z, payload)
                print(struct.pack_into('!HH' + str(taille_msg_entier) + 's',buf,0, taille_msg_entier + 4, z, payload))
                self.processEnvoi(buf, self.dictionnary[host_port].hostPort)
                self.ackRecu(self.dictionnary[host_port].hostPort, num)
                print('message film envoye')

            
        #envoi de la liste des users après reception de l'ack du msg contenant la liste des films
        if (tipe == 63 and num ==2):
            if self.dictionnary[host_port].numeroSequence == num :
                #envoie de la liste des usersnames
                self.dictionnary[host_port].numeroSequence += 1
                octet = (self.dictionnary[host_port].numeroSequence << 6) +0b000011
                taille_msg_liste = 0
                payload_liste = b''
            
                for u in self.serverProxy.getUserList():
                    print ('user name: ', u.userName)
                    print('user location : ', u.userChatRoom)
                    print('user id :', u.userId)
                    print('user adresse ip', u.userChatInstance)

                    #pour l'instant on considère que l'utilisateur est par défaut dans la main room
                    id_salon=0
                    name = u.userName.encode("utf-8")
                    l = len(name)
                    taille_msg_liste = taille_msg_liste + l + 2
                    msg_1 = struct.pack('!BB' + str(l)+'s', l + 2, id_salon, name)
                    payload_liste = payload_liste + msg_1
                    print('payload_liste', payload_liste)
                buf = bytearray(taille_msg_liste + 4) 
                struct.pack_into('!HH' + str(taille_msg_liste) + 's',buf,0, taille_msg_liste + 4, octet, payload_liste)
                self.processEnvoi(buf, self.dictionnary[host_port].hostPort)
                self.ackRecu(self.dictionnary[host_port].hostPort, num)
                print('message user envoye')
                
        #on prévient les autres utilisateurs de l'arrivée du nouvel utilisateur
        if (tipe == 63 and num ==3):
            print(self.dictionnary)
            nouveau = self.dictionnary[host_port].userName
            print(nouveau)
            nouveau_1 = nouveau.encode('utf-8')
            if self.dictionnary[host_port].numeroSequence == num  :
                salon = 0
                taille = len(nouveau_1)
                buf = bytearray(taille + 5)
                print('message dans le buffer')
                for u in self.serverProxy.getUserList():
                    destination = u.userChatInstance
                    self.dictionnary[destination].numeroSequence+=1
                    z = (self.dictionnary[destination].numeroSequence << 6) + 0b000100
                    struct.pack_into( '!HHB' + str(taille) + 's',buf, 0, taille + 5 , z, salon, nouveau_1)
                    self.processEnvoi(buf, self.dictionnary[destination].hostPort)
                    self.ackRecu(self.dictionnary[destination].hostPort, num)

        
        
        #Reception d'un message instantané
        if tipe == 5 :
            if self.dictionnary[host_port].numeroSequenceAttendu == num:
                #envoi de l'ack du msg instantanné
                x = ( num << 6 ) + 0b111111
                taille = 0b100
                ack = struct.pack( '!HH', taille , x)
                print('acquittement prêt à envoyer')
                self.transport.write(ack, host_port)
                self.dictionnary[host_port].numeroSequenceAttendu += 1

            #on cherche la localisation de l'emetteur
            self.userList = self.serverProxy.getUserList()
            username = self.dictionnary[host_port].userName
            userRoom = self.dictionnary[host_port].chatRoom

            print('localisation de user qui envoie le message', userRoom)
            print(self.userList)
            print(self.serverProxy.getUserList())            

            for u in self.serverProxy.getUserList():
                #on envoie le msg instantanée uniquement aux utilisateurs dans la même salle que l'émetteur
                if u.userChatRoom == userRoom:
                    dest = u.userChatInstance
                    print(u.userChatInstance)
                    #construction du message redir_message_instantane
                    self.dictionnary[dest].numeroSequence+=1
                    r = (self.dictionnary[dest].numeroSequence << 6) + 0b001010
                    nom_code=username.encode("utf-8")
                    taille_nom = len(nom_code)
                    taille_payload = 1 + taille_nom + len(data)
                taille_msg = len(data)
                buf = bytearray(taille_payload + 4)
                struct.pack_into('!HHB'+str(taille_nom)+'s'+str(taille_msg)+'s', buf, 0,    taille_payload + 4, r, taille_nom, nom_code, data)
                self.processEnvoi(buf, self.dictionnary[dest].hostPort)
                self.ackRecu(self.dictionnary[dest].hostPort, num)

        
        #demande de rejoindre un salon 
        if tipe == 6 :
            if self.dictionnary[host_port].numeroSequenceAttendu == num:
                #envoie de l'acquittement
                x = ( num << 6 ) + 0b111111
                taille = 0b100
                ack = struct.pack( '!HH', taille , x)
                print('acquittement prêt à envoyer')
                print(ack)
                self.transport.write(ack, host_port)            
                self.dictionnary[host_port].numeroSequenceAttendu += 1
            
            print('id_salon', data)
            data2=struct.unpack('!B', datagram[4:])[0]
            print('id_salon sans buf',data2)
            
            #de la movie room vers la main room
            if data2 == 0 :
                #mise à jour de la localisation de l'utilisateur
                username = self.dictionnary[host_port].userName
                self.serverProxy.updateUserChatroom(username, ROOM_IDS.MAIN_ROOM)
                print('username est',username)
                print(self.serverProxy.getUserList())
                self.dictionnary[host_port].chatRoom = ROOM_IDS.MAIN_ROOM

                
                #envoi du message join_room_ok
                self.dictionnary[host_port].numeroSequence += 1
                x = ( self.dictionnary[host_port].numeroSequence << 6 ) + 0b001011
                taille = 0b100
                buf = bytearray(taille)
                struct.pack_into( '!HH', buf, 0, taille , x)
                self.processEnvoi(buf, self.dictionnary[host_port].hostPort)
                self.ackRecu(self.dictionnary[host_port].hostPort, num)
                
                
                #mise a jour utilisateur
                for u in self.serverProxy.getUserList():
                    destination = u.userChatInstance
                    self.dictionnary[destination].numeroSequence+=1
                    z = (self.dictionnary[destination].numeroSequence << 6) + 0b000100         
                    name = username.encode("utf-8")
                    l = len(name)
                    buf = bytearray(l+5)
                    struct.pack_into( '!HHB' + str(l) + 's', buf, 0, l + 5 , z, 0 , name)
                    self.processEnvoi(buf, self.dictionnary[destination].hostPort)
                    self.ackRecu(self.dictionnary[destination].hostPort, num+1)

            #de la main room à la movie room
            else :
                validite_room = 0
                for m in self.serverProxy.getMovieList():
                    print(self.serverProxy.getMovieList())
                    print("identifiant:", m.movieId)
                    id_salon = struct.pack('!B', m.movieId)

                    if id_salon == data :
                        validite_room = 1
                        print('demande acceptée')
                        #mise à jour de la localisation de l'utilisateur
                        username = self.dictionnary[host_port].userName
                        self.serverProxy.updateUserChatroom(username, str(m.movieId))
                        print('username est',username)
                        print(str(m.movieId))
                        print(' regarde un film', self.serverProxy.getUserList())
                        room = struct.unpack('!B', id_salon)[0]
                        self.dictionnary[host_port].chatRoom =  str(room)
                        print('room :', room)
                        
                        #message joindre_salon_ok
                        self.dictionnary[host_port].numeroSequence += 1
                        x = ( self.dictionnary[host_port].numeroSequence << 6 ) + 0b001011
                        taille = 0b100
                        buf = bytearray(taille)
                        struct.pack_into( '!HH', buf, 0, taille , x)
                        self.processEnvoi(buf, self.dictionnary[host_port].hostPort)
                        self.ackRecu(self.dictionnary[host_port].hostPort, num)
                        
                        movie_title = m.movieTitle                    
                        self.serverProxy.startStreamingMovie(movie_title)
                        
                        
                        #on prévient les autres clients qu'un nouvel utilisateur s'est connecté
                        for u in self.serverProxy.getUserList():
                            destination = u.userChatInstance
                            self.dictionnary[destination].numeroSequence+=1
                            z = (self.dictionnary[destination].numeroSequence << 6) + 0b000100         
                            name = username.encode("utf-8")
                            l = len(name)                            
                            buf = bytearray(l + 5)
                            struct.pack_into( '!HHB' + str(l) + 's', buf, 0, l + 5 , z, m.movieId, name)
                            self.processEnvoi(buf, self.dictionnary[destination].hostPort)
                            self.ackRecu(self.dictionnary[destination].hostPort, num + 1)

                #la demande de film est incorrect
                if validite_room == 0:    
                    print('demande refusee')
                    self.dictionnary[host_port].numeroSequence += 1
                    x = ( self.dictionnary[host_port].numeroSequence << 6 ) + 0b001100
                    taille = 0b100
                    buf = bytearray(taille)
                    struct.pack_into( '!HH', buf, 0, taille , x)
                    self.processEnvoi(buf, self.dictionnary[host_port].hostPort)
                    self.ackRecu(self.dictionnary[host_port].hostPort, num)
                    




        
        #Demande de deconnexion
        if (tipe == 0b001001):
            #envoi de l'ack de la demande de deconnexion
            if self.dictionnary[host_port].numeroSequenceAttendu == num:
                x = ( num << 6 ) + 0b111111
                taille = 0b100
                ack = struct.pack( '!HH', taille , x)
                print('acquittement demande deconnexion')
                self.transport.write(ack, host_port)
                self.dictionnary[host_port].numeroSequenceAttendu += 1
            
            ###localisation de l'utilisateur
            userRoom = self.dictionnary[host_port].chatRoom
            username = self.dictionnary[host_port].userName
            print('deconnexion',userRoom)
            
            
            if (userRoom == ROOM_IDS.MAIN_ROOM) :
                print('je suis dans la main room',userRoom)
                self.serverProxy.removeUser(username)
                userRoom = 255
                print(self.serverProxy.getUserList())
                
               
            #on prévient les autres clients qu'un utilisateur s'est deconnecté
            print(userRoom)
            for u in self.serverProxy.getUserList():
                destination = u.userChatInstance            
                self.dictionnary[destination].numeroSequence += 1
                z = (self.dictionnary[destination].numeroSequence << 6) + 0b000100
                name = username.encode("utf-8")
                print(name)
                l = len(name)
                print(l)
                buf = bytearray(l + 5)
                struct.pack_into( '!HHB' + str(l) + 's', buf, 0, l+4+1, z, userRoom, name)
                self.processEnvoi(buf, self.dictionnary[destination].hostPort)
                self.ackRecu(self.dictionnary[destination].hostPort, num)
                
            

        
        
    ######FIABILITE
    def sendAndWait (self,buf,host_port) :
        print('liste d attente :', self.dictionnary[host_port].file)
        self.dictionnary[host_port].etatAck=0 
        if (self.dictionnary[host_port].counter <= 10):
            self.dictionnary[host_port].counter+=1
            self.transport.write(buf,self.dictionnary[host_port].hostPort)
            print('le message est envoyé', buf)
            self.dictionnary[host_port].timer=reactor.callLater(1,self.sendAndWait,buf,host_port)
        elif (self.dictionnary[host_port].counter > 10):
            self.dictionnary[host_port].timer=None
            self.serverProxy.removeUser(self.dictionnary[host_port].userName)
        
    def ackRecu(self,host_port,seq):
        print('reception acquittement : on verifie')
        print('num seq', seq)
        print('prochain num sequ:',self.dictionnary[host_port].nextNumSeq)
        if  (self.dictionnary[host_port].nextNumSeq==seq):
            self.dictionnary[host_port].nextNumSeq = (self.dictionnary[host_port].nextNumSeq + 1)
            self.dictionnary[host_port].timer.cancel()
            self.dictionnary[host_port].counter=0
            self.dictionnary[host_port].etatAck=1
            if (self.dictionnary[host_port].file ==[]):
                print('rien a envoyé')
                pass
            else:
                print('premier message file d attente')
                self.sendAndWait(self.dictionnary[host_port].file[0],self.dictionnary[host_port].hostPort) 
                messageSent(self.dictionnary[host_port].file)

    def processEnvoi(self,buf,host_port):
        print('le message est dans le procédure denvoi')
        print('destinataire :', self.dictionnary[host_port].userName)
        print('etat ack :', self.dictionnary[host_port].etatAck==1)
        if (self.dictionnary[host_port].file == []) and (self.dictionnary[host_port].etatAck==1):
            ('le message va dans le send and wait')
            self.sendAndWait(buf,host_port)
        else:
            messageToSend(self.dictionnary[host_port].file, buf)
            print('le message est ajoute a la liste d attente')


