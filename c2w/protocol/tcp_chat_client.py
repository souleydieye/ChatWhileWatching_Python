# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol
import logging
import struct
from c2w.main.constants import ROOM_IDS

logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.tcp_chat_client_protocol')


class c2wTcpChatClientProtocol(Protocol):

    def __init__(self, clientProxy, serverAddress, serverPort):
        """
        :param clientProxy: The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.
        :param serverAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param serverPort: The port number used by the c2w server,
            given by the user.

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attribute:

        .. attribute:: clientProxy

            The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        .. attribute:: serverAddress

            The IP address of the c2w server.

        .. attribute:: serverPort

            The port number used by the c2w server.

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
        """

        #: The IP address of the c2w server.
        self.serverAddress = serverAddress
        #: The port number used by the c2w server.
        self.serverPort = serverPort
        #: The clientProxy, which the protocol must use
        #: to interact with the Graphical User Interface.
        self.clientProxy = clientProxy
        self.userName =''
        self.numeroSequence = 0
        self.msg_total = b''
        self.listFilm = []
        self.IDFilm = []
        self.listUser = []
        
    def sendLoginRequestOIE(self, userName):
        """
        :param string userName: The user name that the user has typed.

        The client proxy calls this function when the user clicks on
        the login button.
        """
        moduleLogger.debug('loginRequest called with username=%s', userName)
        
        self.userName= userName
        
        self.numeroSequence=self.numeroSequence + 1
        tipe = 0b000001
        z = ( self.numeroSequence << 6 ) + tipe 
        data = userName.encode("utf-8")
        taille = len (data) + 4
        
        message = struct.pack( '!HH' + str(taille-4) +'s', taille , z ,  data)
        print('requête de connexion')
        self.transport.write(message)
        

    def sendChatMessageOIE(self, message):
        """
        :param message: The text of the chat message.
        :type message: string

        Called by the client proxy when the user has decided to send
        a chat message

        .. note::
           This is the only function handling chat messages, irrespective
           of the room where the user is.  Therefore it is up to the
           c2wChatClientProctocol or to the server to make sure that this
           message is handled properly, i.e., it is shown only by the
           client(s) who are in the same room.
        """
        
        self.numeroSequence = self.numeroSequence + 1
        tipe = 0b000101
        z = ( self.numeroSequence << 6 ) + tipe
        data = message.encode("utf-8")
        taille = len (data) + 4
        message_chat = struct.pack( '!HH' + str(taille-4) +'s', taille , z ,  data)
        self.transport.write(message_chat)
        

    def sendJoinRoomRequestOIE(self, roomName):
        """
        :param roomName: The room name (or movie title.)

        Called by the client proxy  when the user
        has clicked on the watch button or the leave button,
        indicating that she/he wants to change room.

        .. warning:
            The controller sets roomName to
            c2w.main.constants.ROOM_IDS.MAIN_ROOM when the user
            wants to go back to the main room.
        """
        #on incrémente le numero de sequence
        self.numeroSequence = self.numeroSequence + 1
        # On construit le message
        longueur = 5
        tipe = 0b000110
        z = ( self.numeroSequence << 6 ) + tipe 
        ID_Salon =0
        
        
        if roomName == 'MainRoom' :
            ID_Salon = 0b00000000

        else :
            for n in range(len(self.IDFilm)):
                if self.IDFilm[n][0] == roomName :
                    ID_Salon = self.IDFilm[n][1]
        #si l'utilisateur entre un roomName inexistant, l'ID_Salon reste a 0 et le serveur enverra un JOINDRE_SALON_NOK
        requete_salon = struct.pack( '!HHB', longueur , z , ID_Salon)
        self.transport.write(requete_salon)

    def sendLeaveSystemRequestOIE(self):
        """
        Called by the client proxy  when the user
        has clicked on the leave button in the main room.
        """
        #on incrémente le numero de sequence
        self.numeroSequence = self.numeroSequence + 1
        # On construit le message
        longueur = 4
        tipe = 0b001001

        z = ( self.numeroSequence << 6 ) + tipe 
        deconnexion = struct.pack( '!HH', longueur , z)
        self.transport.write(deconnexion)
        print('je quitte l application')
        self.clientProxy.leaveSystemOKONE()

    def dataReceived(self, data):
        """
        :param data: The data received from the client (not necessarily
                     an entire message!)

        Twisted calls this method whenever new data is received on this
        connection.
        """
        print('reception d un paquet')
        
        self.msg_total = self.msg_total + data
        
        print('on recoit :', self.msg_total)        
        print(len(self.msg_total))
        
        
        if len(self.msg_total)>2 :
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

        
                
                if tipe1 == 63 :
                    print(self.msg_total)
                    print("on a recu un acquittement")
                    
                
                #connexion acceptée
                if tipe1 == 7 :
                    print('la connection est acceptée')
                    print("on envoie un acquittement")
                    Type = 0b111111
                    z = ( num1<<6 ) + Type 
                    taille = 0b100
                    message = struct.pack( '!HH' , taille , z ) 
                    self.transport.write(message)
                    
               #La connection est refusée
                if tipe1 == 0b001000 : 
                    data2=struct.unpack('!B', datagram[4:])[0]
                    if data2 == 0b00000001 :
                        self.clientProxy.connectionRejectedONE('nom deja utilise')
                    if data2 == 0b00000010 :
                        self.clientProxy.connectionRejectedONE('nom trop long')
                    if data2 == 0b00000011 :
                        self.clientProxy.connectionRejectedONE('nom contenant un ou plusieurs espaces')

               
                #reception de la liste des films
                if tipe1 == 2 :
                    #envoi ack
                    Type = 0b111111
                    z = ( num1<<6 ) + Type 
                    taille = 0b100
                    message = struct.pack( '!HH' , taille , z )    
                    self.transport.write(message)
                    
                    print('corps du message', datagram)
                    
                    
                    #on stocke la liste des films
                    l=0
                    while l != (longueur-4):

                        length = struct.unpack('!B',corps_message[l:1+l])[0]
                        print(length)
                
                        ip_salon = struct.unpack('!i',corps_message[1+l:5+l])[0] 
                        port_salon = struct.unpack('!H', corps_message[5+l:7+l])[0]
                        id_salon = struct.unpack('!B' , corps_message[7+l:8+l])[0]
                        film_name = struct.unpack(str(length-8)+'s', corps_message[8+l : (length+l)])[0]
                        l = l +length
                        self.listFilm = self.listFilm + [(film_name.decode('utf-8'), ip_salon, port_salon)]
                        self.IDFilm = self.IDFilm + [(film_name.decode('utf-8'),id_salon)]                    
                    print(self.listFilm)
               
                #reception de la liste des users
                if tipe1 ==3  :
                    self.listUser = []
                    #envoi ack
                    Type = 0b111111
                    z = ( num1<<6 ) + Type 
                    taille = 0b100
                    message = struct.pack( '!HH' , taille , z )    
                    self.transport.write(message)
                    
                    #on stocke la liste des users
                    l=0
                    while l != (longueur-4):

                        length1 = struct.unpack('!B',corps_message[l:1+l])[0]
                        id_salon = struct.unpack('!B' , corps_message[1+l:2+l])[0]
                        print('id salon utilisateur', id_salon)
                        user_name = struct.unpack(str(length1-2)+'s', corps_message[2+l : (length1+l)])[0]
                        l = l +length1
               
                
                        self.listUser = self.listUser + [(user_name.decode('utf-8'), ROOM_IDS.MAIN_ROOM )]
  
                    #affichage des listes films et utilisateurs
                    print('liste user', self.listUser)
                    self.clientProxy.initCompleteONE(self.listUser, self.listFilm)
                    print('utlisation de init')
                    
                #mise à jour utilisateur
                if tipe1 == 0b000100:
                    print('nouvel utilisateur', corps_message)
                    #ack msg mise a jour
                    Type = 0b111111
                    z = ( num1<<6 ) + Type 
                    taille = 0b100
                    message = struct.pack( '!HH' , taille , z )    
                    self.transport.write(message)
                
            
                    salle = struct.unpack('!B', corps_message[:1])[0]
                    nom = struct.unpack(str(len(corps_message)-1)+'s', corps_message[1:])[0]
                    print('salle', salle)
                    print('nom nvl utilisateur', nom)
                    nom1 = self.userName.encode('utf-8')
                    print('nom1', nom1)
            
                    #un nouvel utilisateur vient d'arriver dans la main room
                    if salle ==0 : 
                        salle = ROOM_IDS.MAIN_ROOM 
                        print(salle)
                        
                    m = (nom.decode('utf-8'), ROOM_IDS.MAIN_ROOM)
                    i = m in self.listUser
                    print('utilisateur existant mise à jour loca')
                    if i == True and salle!=ROOM_IDS.MAIN_ROOM :
                        
                        if salle == 255:
                            for i in self.listUser : 
                                print('liste user',i[0])
                                print('gone', nom.decode('utf-8'))
                                if i[0]== nom.decode('utf-8') :
                                    self.listUser.remove(i)
                                    print(self.listUser)
                                    self.clientProxy.setUserListONE(self.listUser)
                        else:
                            for u in self.IDFilm : 
                                if u[1]==salle:
                                        self.clientProxy.userUpdateReceivedONE(nom.decode('utf-8'), u[0])
                                        
                    elif i==True and salle == ROOM_IDS.MAIN_ROOM:
                        print('retour en main room ou arrivéé en main room')
                        for i in self.listUser : 
                            if i[0] == nom.decode('utf-8'):
                                self.clientProxy.userUpdateReceivedONE(nom.decode('utf-8'), ROOM_IDS.MAIN_ROOM)
                        

                    elif i==False:
                        self.listUser = self.listUser + [(nom.decode('utf-8'), ROOM_IDS.MAIN_ROOM)]
                        print(self.listUser)
                        self.clientProxy.setUserListONE(self.listUser)
                
                #reception d'un message de chat
                if tipe1 == 0b001010:                    
                    #on envoie un acquittement
                    Type = 0b111111
                    z = ( num1<<6 ) + Type 
                    taille = 0b100
                    message = struct.pack( '!HH' , taille , z )    
                    self.transport.write(message)
                        
                    
                    #on decode le message
                    taille_user = struct.unpack('!B', corps_message[:1])[0]
                    nom_emetteur = struct.unpack('!' +str(taille_user)+'s', corps_message[1:1+taille_user])[0]
                    texte_message = struct.unpack('!' + str(longueur - 4 -1- taille_user) +'s', corps_message[1+taille_user:])[0]
                    chat = texte_message.decode('utf-8')
                  
                    print('emetteur', nom_emetteur)
                    if nom_emetteur.decode('utf-8')!= self.userName:                
                        self.clientProxy.chatMessageReceivedONE(nom_emetteur.decode('utf-8'), texte_message.decode('utf-8'))
                
                #validation de la requete de joindre une room
                if tipe1 == 0b001011:
                    Type = 0b111111
                    z = ( num1<<6 ) + Type 
                    taille = 0b100
                    message = struct.pack( '!HH' , taille , z )    
                    self.transport.write(message)
                    print('on va rejoindre la movie room')
                    self.clientProxy.joinRoomOKONE()
                
                
                self.dataReceived(bytes(0))

