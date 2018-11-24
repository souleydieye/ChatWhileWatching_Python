# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol
import logging
import struct
from c2w.main.constants import ROOM_IDS
logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.tcp_chat_server_protocol')


class c2wTcpChatServerProtocol(Protocol):

    def __init__(self, serverProxy, clientAddress, clientPort):
        """
        :param serverProxy: The serverProxy, which the protocol must use
            to interact with the user and movie store (i.e., the list of users
            and movies) in the server.
        :param clientAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param clientPort: The port number used by the c2w server,
            given by the user.

        Class implementing the TCP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attribute:

        .. attribute:: serverProxy

            The serverProxy, which the protocol must use
            to interact with the user and movie store in the server.

        .. attribute:: clientAddress

            The IP address of the client corresponding to this 
            protocol instance.

        .. attribute:: clientPort

            The port number used by the client corresponding to this 
            protocol instance.

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.

        .. note::
            The IP address and port number of the client are provided
            only for the sake of completeness, you do not need to use
            them, as a TCP connection is already associated with only
            one client.
        """
        #: The IP address of the client corresponding to this 
        #: protocol instance.
        self.clientAddress = clientAddress
        #: The port number used by the client corresponding to this 
        #: protocol instance.
        self.clientPort = clientPort
        #: The serverProxy, which the protocol must use
        #: to interact with the user and movie store in the server.
        self.serverProxy = serverProxy
        self.msg_total = b''
        self.nbrAckRecu =0
        self.numeroSequence = 0
        self.userList = []
        self.dictionnary = {}
        self.userName = ''
        self.userRoom = ''

    def dataReceived(self, data):
        """
        :param data: The data received from the client (not necessarily
                     an entire message!)

        Twisted calls this method whenever new data is received on this
        connection.
        """
        
        ### FRAMING ###
        print('reception d un paquet')
        client = (self.clientAddress, self.clientPort)
        self.msg_total = self.msg_total + data
        print('taille:', len(self.msg_total))
        if len(self.msg_total)>=4 :
            reste1=struct.unpack('!H', self.msg_total[2:4])[0] #deux octets contenant le numero de seq et le type
            longueur=struct.unpack('!H', self.msg_total[:2])[0] #recuperation des 2 premiers octets
            num1 = (reste1 & 0b1111111111000000) >> 6 
            tipe1 = (reste1 & 0b0000000000111111)
            print('le type est', tipe1)
            print('longueur du msg', longueur)
            print('longueur de la trame', len(self.msg_total))
            
            if (len(self.msg_total) >= longueur):
                #on a recu un message en entier et un bout de message
                datagram = self.msg_total[0:longueur]
                print(datagram)
                self.msg_total = self.msg_total[longueur :]
                print('nouveau msg total', self.msg_total)                          
                
                #donnée du premier message
                corps_message = struct.unpack(str(longueur - 4)+'s', datagram[4:])[0]
                print('corps du msg :', corps_message)
                

                #reception d'une requête d'inscription
                if tipe1 == 1:
                    self.nbrAckRecu =0
                    #envoi de l'acquittement
                    print('envoi acquittement demande d inscription')
                    Type = 0b111111
                    z = ( num1<<6 ) + Type 
                    taille = 0b100
                    message = struct.pack( '!HH' , taille , z )
                    print('ACK :', message)
                    self.transport.write(message)

                    #verification requete inscription (space, too long)                     
                    username = corps_message.decode("utf-8")                                        
                    erreur = 0
                    for i in range(0, len(self.userList)-1) : 
                        if(self.userList[i]==username) : #verification de l'unicité du login
                            erreur = 0b00000001
                    if (len(data)>254): #login trop long
                        erreur = 0b00000010
                    is_space = ' ' in username
                    if is_space == True:
                        erreur = 0b00000011
                    print('l erreur est' + str(erreur))
                  
                    if erreur == 0:
                        #envoi du message inscription acceptée
                        self.numeroSequence = self.numeroSequence + 1
                        tipe = 0b000111
                        z = ( self.numeroSequence << 6 ) + tipe
                        taille_msg_ok = 0b100
                        message_ins_ok = struct.pack( '!HH', taille_msg_ok, z )
                        print('message inscription :',message_ins_ok)
                        self.transport.write(message_ins_ok)                    

                    
                        #on ajoute l'utilisateur à la liste
                        username = corps_message.decode("utf-8")
                        print(username)
                        self.userName = username
                    
                        self.serverProxy.addUser(username, ROOM_IDS.MAIN_ROOM, self)
                    

                        self.userList = self.serverProxy.getUserList()
                        self.userRoom=ROOM_IDS.MAIN_ROOM

                        print('liste utilisateur', self.userList)

                    else:
                        #on envoie le message d'inscription refusée
                        self.numeroSequence += 1
                        Type = 0b001000
                        z = ( self.numeroSequence << 6 ) + Type 
                        taille = 0b101
                        buf = bytearray(taille)
                        no_inscription = struct.pack( '!HHB' ,taille , z, erreur)
                        self.transport.write(no_inscription)

                #envoi liste film
                if tipe1 == 63 and num1==1 :
                    #envoie de la liste de film
                    self.numeroSequence += 1
                    z = (self.numeroSequence << 6) + 0b000010
                    taille_msg_entier =0
                    payload = b''
                    print('on parcourt la liste des films')
                
                    for m in self.serverProxy.getMovieList():
                        print("Movie title :", m.movieTitle)
                        print("IP Salon :", m.movieIpAddress)
                        ip= m.movieIpAddress.split(".")                               
                        print("le port:", m.moviePort)
                        print("identifiant:", m.movieId)
                        data1 = m.movieTitle.encode("utf-8")
                        taille = len(data1)
                        taille_msg_entier = taille_msg_entier + taille + 8
                        liste=struct.pack('!BBBBBHB' + str(taille) +'s' , taille+8, int(ip[0]), int(ip[1]), int(ip[2]), int(ip[3]), m.moviePort, m.movieId, data1)
                    
                        payload = payload + liste
                        print('le payload est :', payload)
                        print('taille du message : ', taille_msg_entier)
                    msg_film = struct.pack('!HH' + str(taille_msg_entier) + 's', taille_msg_entier + 4, z, payload)
                    print('msg film:', msg_film)
                    self.transport.write(msg_film)
                    print('message film envoye')
                
                #envoi liste des utilisateurs
                if tipe1 == 63 and num1==2: 
                    self.numeroSequence += 1
                    octet = (self.numeroSequence << 6) +0b000011
                    taille_msg_liste = 0
                    payload_liste = b''
                    print (self.serverProxy.getUserList())
            
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
                    msg_user = struct.pack('!HH' + str(taille_msg_liste) + 's', taille_msg_liste + 4, octet, payload_liste)
                    print('msg_user :', msg_user)
                    self.transport.write(msg_user)
                    print('message user envoye')
                    
                #mise à jour utilisateurs
                if tipe1 == 63 and num1==3:
                    nouveau = self.userName
                    nouveau_1 = nouveau.encode('utf-8')
                    print('nom du nouvel utilisateur', nouveau)
                    salon = 0
                    taille = len(nouveau_1)
                    for u in self.serverProxy.getUserList():
                        destination = u.userChatInstance
                        self.numeroSequence +=1
                        z = (self.numeroSequence << 6) + 0b000100
                        msg_mise_jour = struct.pack( '!HHB' + str(taille) + 's', taille + 5 , z, salon, nouveau_1)
                        u.userChatInstance.transport.write(msg_mise_jour)

                #Reception d'un message instantané
                if tipe1 == 5 :                    
                    #envoi de l'ack du msg instantanné
                    x = ( num1 << 6 ) + 0b111111
                    taille = 0b100
                    ack = struct.pack( '!HH', taille , x)
                    print('acquittement prêt à envoyer')
                    self.transport.write(ack)                        

                    #on cherche la localisation de l'emetteur
                    self.userList = self.serverProxy.getUserList()
                    print('localisation de user qui envoie le message', self.userRoom)
                    print(self.userList)
                    print(self.serverProxy.getUserList())            
                    #envoie du message aux utilisateurs présents dans la meme room que l'émetteur
                    for u in self.serverProxy.getUserList():
                        print('lautre utilisateur est dans la salle', u.userChatRoom)
                        print('localisation emetteur', self.userRoom)
                        print('test',u.userChatRoom == str(self.userRoom))
                        
                        if u.userChatRoom == self.userRoom:
                            #construction du message redir_message_instantane
                            self.numeroSequence+=1
                            r = (self.numeroSequence << 6) + 0b001010
                            nom_code=self.userName.encode("utf-8")
                            taille_nom = len(nom_code)
                            taille_payload = 1 + taille_nom + len(corps_message)
                        taille_msg = len(corps_message)
                        msg_redir = struct.pack('!HHB'+str(taille_nom)+'s'+str(taille_msg)+'s',    taille_payload + 4, r, taille_nom, nom_code, corps_message )
                        u.userChatInstance.transport.write(msg_redir)

                #demande de rejoindre un salon 
                if tipe1 == 6 :                    
                    #envoie de l'acquittement
                    x = ( num1 << 6 ) + 0b111111
                    taille = 0b100
                    ack = struct.pack( '!HH', taille , x)
                    print('acquittement prêt à envoyer')
                    print(ack)
                    self.transport.write(ack)            
                        
                    
                    print('id_salon', data)
                    data2=struct.unpack('!B', datagram[4:])[0]
                    print('id_salon sans buf',data2)
                    
                    #de la movie room vers la main room
                    if data2 == 0 :
                        self.serverProxy.updateUserChatroom(self.userName, ROOM_IDS.MAIN_ROOM)
                        print('username est',self.userName)
                        print(self.serverProxy.getUserList())
                        self.userRoom = ROOM_IDS.MAIN_ROOM
                       
                        #envoi du message join_room_ok
                        self.numeroSequence += 1
                        x = ( self.numeroSequence << 6 ) + 0b001011
                        taille = 0b100
                        
                        msg_joindre_ok = struct.pack( '!HH', taille , x)
                        self.transport.write(msg_joindre_ok)
                        
                        
                        #mise a jour utilisateur
                        for u in self.serverProxy.getUserList():
                            destination = u.userChatInstance
                            self.numeroSequence+=1
                            z = (self.numeroSequence << 6) + 0b000100         
                            name = self.userName.encode("utf-8")
                            l = len(name)
                            
                            msg_mise_jour = struct.pack( '!HHB' + str(l) + 's',  l + 5 , z, 0 , name)
                            u.userChatInstance.transport.write(msg_mise_jour)

                    #de la main room à la movie room
                    else :
                        validite_room = 0
                        for m in self.serverProxy.getMovieList():
                            print(self.serverProxy.getMovieList())
                            print("identifiant:", m.movieId)
                            id_salon = struct.pack('!B', m.movieId)

                            if id_salon == corps_message :
                                validite_room = 1
                                print('demande acceptée')
                                #mise à jour de la localisation de l'utilisateur
                                self.serverProxy.updateUserChatroom(self.userName, str(m.movieId))
                                print('username est',self.userName)
                                print(str(m.movieId))
                                print(' regarde un film', self.serverProxy.getUserList())
                                room = struct.unpack('!B', id_salon)[0]
                                self.userRoom = str(room)
                                print('room :', room)
                                
                                #message joindre_salon_ok
                                self.numeroSequence += 1
                                x = ( self.numeroSequence << 6 ) + 0b001011
                                taille = 0b100
                                chgmt_room = struct.pack( '!HH', taille , x)
                                self.transport.write(chgmt_room)

                                
                                movie_title = m.movieTitle                    
                                self.serverProxy.startStreamingMovie(movie_title)
                                
                                
                                #on prévient les autres clients qu'un nouvel utilisateur s'est connecté
                                for u in self.serverProxy.getUserList():
                                    destination = u.userChatInstance
                                    self.numeroSequence+=1
                                    z = (self.numeroSequence << 6) + 0b000100         
                                    name = self.userName.encode("utf-8")
                                    l = len(name)                            
                                    msg_mise_jour = struct.pack( '!HHB' + str(l) + 's', l + 5 , z, m.movieId, name)
                                    u.userChatInstance.transport.write(msg_mise_jour)


                        #la demande de film est incorrect
                        if validite_room == 0:    
                            print('demande refusee')
                            self.numeroSequence += 1
                            x = ( self.numeroSequence << 6 ) + 0b001100
                            taille = 0b100
                            
                            refus = struct.pack( '!HH', taille , x)
                            self.transport.write(refus)

                #Demande de deconnexion
                if (tipe1 == 0b001001):
                    #envoi de l'ack de la demande de deconnexion
                    x = ( num1 << 6 ) + 0b111111
                    taille = 0b100
                    ack = struct.pack( '!HH', taille , x)
                    print('acquittement demande deconnexion')
                    self.transport.write(ack)
                    
                    if (self.userRoom == ROOM_IDS.MAIN_ROOM) :
                        print('je suis dans la main room',self.userRoom)
                        self.serverProxy.removeUser(self.userName)
                        self.userRoom = 255
                        print(self.serverProxy.getUserList())

                    #on prévient les autres clients qu'un utilisateur s'est deconnecté
                    for u in self.serverProxy.getUserList():
                        destination = u.userChatInstance            
                        self.numeroSequence += 1
                        z = (self.numeroSequence << 6) + 0b000100
                        name = self.userName.encode("utf-8")
                        print(name)
                        l = len(name)
                        print(l)
                        msg_deco = struct.pack( '!HHB' + str(l) + 's', l+4+1, z, self.userRoom, name)
                        u.userChatInstance.transport.write(msg_deco)

                
                    
                
                self.dataReceived(bytes(0))

