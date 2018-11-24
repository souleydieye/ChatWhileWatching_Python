# -*- coding: utf-8 -*-
from twisted.internet.protocol import DatagramProtocol
from c2w.main.lossy_transport import LossyTransport
import struct
import logging
from twisted.internet import reactor
from c2w.main.constants import ROOM_IDS

logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.udp_chat_client_protocol')

#gestion de la file d'attente des message
#on enlève le message qui vient d'être envoyé
def messageSent(file):
    file.pop(0)
    return

#ajout d'un message à la file d'attente
def messageToSend(file, message):
    file.append(message)
    return

class c2wUdpChatClientProtocol(DatagramProtocol):

    def __init__(self, serverAddress, serverPort, clientProxy, lossPr):
        """
        :param serverAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param serverPort: The port number used by the c2w server,
            given by the user.
        :param clientProxy: The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attributes:

        .. attribute:: serverAddress

            The IP address of the c2w server.

        .. attribute:: serverPort

            The port number of the c2w server.

        .. attribute:: clientProxy

            The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        .. attribute:: lossPr

            The packet loss probability for outgoing packets.  Do
            not modify this value!  (It is used by startProtocol.)

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
        """

        #: The IP address of the c2w server.
        self.serverAddress = serverAddress
        #: The port number of the c2w server.
        self.serverPort = serverPort
        #: The clientProxy, which the protocol must use
        #: to interact with the Graphical User Interface.
        self.clientProxy = clientProxy
        self.lossPr = lossPr

        #: stocker le numéro de séquence
        self.numeroSequence = 0
        self.numeroSequenceAttendu = 1
        self.listFilm = []
        self.listUser = []
        self.IDFilm = []
        self.file = []
        self.counter = 0
        self.timer = None
        self.numSequenceServeur = 0
        self.etatAck = 1 #vaut 1 si le message a ete acquitte, 0 sinon
        self.seqNumAck = 0 
        self.userName = ''




    def startProtocol(self):
        """
        DO NOT MODIFY THE FIRST TWO LINES OF THIS METHOD!!

        If in doubt, do not add anything to this method.  Just ignore it.
        It is used to randomly drop outgoing packets if the -l
        command line option is used.
        """
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport

    def sendLoginRequestOIE(self, userName):
        """
        :param string userName: The user name that the user has typed.

        The client proxy calls this function when the user clicks on
        the login button.
        """
        print('demande de connexion')
        moduleLogger.debug('loginRequest called with username=%s', userName)
        #on incrémente le numéro de séquence et on convertit en binaire
        self.numeroSequence=self.numeroSequence + 1

        #type Inscription en binaire, sur 6 bits
        tipe = 0b000001
        print('le type est', tipe)

        #construction de deux octets comprenant le numéro de séquence et le type
        z = ( self.numeroSequence << 6 ) + tipe 
        print(z)

        #on code le username
        data = userName.encode("utf-8")
        print(data)

        #taille de l'ensemble du message
        taille = len (data) + 4
        print(taille)
        self.userName= userName
        
        buf = bytearray(taille)

        #construction de la trame
        struct.pack_into( '!HH' + str(taille-4) +'s',buf,0, taille , z ,  data)
        self.processEnvoi(buf)


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
        buf = bytearray(longueur)
        
        if roomName == 'MainRoom' :
            ID_Salon = 0b00000000

        else :
            #on cherche l'identifiant de la salle demandé par l'utilisateur
            for n in range(len(self.IDFilm)):
                if self.IDFilm[n][0] == roomName :
                    ID_Salon = self.IDFilm[n][1]
        #si l'utilisateur entre un roomName inexistant, l'ID_Salon reste a 0 et le serveur enverra un JOINDRE_SALON_NOK
        struct.pack_into( '!HHB',buf,0, longueur , z , ID_Salon)
        self.processEnvoi(buf)
        
    
    def sendChatMessageOIE(self, message):
        self.numeroSequence = self.numeroSequence + 1
        tipe = 0b000101
        #construction de deux octets comprenant le numéro de séquence et le type
        z = ( self.numeroSequence << 6 ) + tipe
        #on code le message
        data = message.encode("utf-8")
        #taille de l'ensemble du message
        taille = len (data) + 4
        #construction de la trame
        buf = bytearray(taille)
        struct.pack_into( '!HH' + str(taille-4) +'s',buf, 0, taille , z ,  data)
        #On envoie le message au serveur
        self.processEnvoi(buf)
        


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
        buf = bytearray(longueur)
        struct.pack_into( '!HH', buf,0, longueur , z)
        self.processEnvoi(buf)       
        print('je quitte l application')
        self.clientProxy.leaveSystemOKONE()

   
    def datagramReceived(self, datagram, host_port):
        """
        :param string datagram: the payload of the UDP packet.
        :param host_port: a touple containing the source IP address and port.

        Called **by Twisted** when the client has received a UDP
        packet.
        """
                
        #decodage du message du message reçu
        print(datagram)
        reste=struct.unpack('!H', datagram[2:4])[0] #deux octets contenant le numero de seq et le type
        longueur=struct.unpack('!H', datagram[:2])[0] #recuperation des 2 premiers octets
        data = struct.unpack(str(longueur-4)+'s', datagram[4:])[0] #recuperation du payload
        num = (reste & 0b1111111111000000) >> 6 
        tipe = (reste & 0b0000000000111111) 
        print("\t\t\ttype {} data {} seq {} ".format(tipe, data, num))

        if tipe==63 :
            print("reception acquittement")
            self.seqNumAck = num 
            self.ackRecu()

        #La connection est acceptee
        if tipe == 0b000111 :
            print('connection en cours')
            if self.numeroSequenceAttendu == num:
                #envoi d'un acquittement
                Type = 0b111111
                z = ( num<<6 ) + Type 
                taille = 0b100
                message = struct.pack( '!HH' , taille , z )
                print('connection acceptée')
                self.transport.write(message, host_port)
                self.numeroSequenceAttendu +=1

        
        #La connection est refusée
        if tipe == 0b001000 : 
            data2=struct.unpack('!B', datagram[4:])[0]
            if data2 == 0b00000001 :
                self.clientProxy.connectionRejectedONE('nom deja utilise')
            if data2 == 0b00000010 :
                self.clientProxy.connectionRejectedONE('nom trop long')
            if data2 == 0b00000011 :
                self.clientProxy.connectionRejectedONE('nom contenant un ou plusieurs espaces')

        #on recoit un message contenant la liste des films
        if tipe == 0b000010 :
            print('reception de la liste des films')
            #on envoie un acquittement attestant la la reception de la liste des films 
            if self.numeroSequenceAttendu == num:
                Type = 0b111111
                z = ( num<<6 ) + Type 
                taille = 0b100
                message = struct.pack( '!HH' , taille , z )    
                self.transport.write(message, host_port)
                self.numeroSequenceAttendu +=1
            
            #on stocke la liste des films
            l=0
            while l != (longueur-4):

                length = struct.unpack('!B',data[l:1+l])[0]
                
                ip_salon = struct.unpack('!i',data[1+l:5+l])[0] 
                port_salon = struct.unpack('!H', data[5+l:7+l])[0]
                id_salon = struct.unpack('!B' , data[7+l:8+l])[0]
                film_name = struct.unpack(str(length-8)+'s', data[8+l : (length+l)])[0]
                l = l +length
                self.listFilm = self.listFilm + [(film_name.decode('utf-8'), ip_salon, port_salon)]
                self.IDFilm = self.IDFilm + [(film_name.decode('utf-8'),id_salon)]
            
            print(self.listFilm)

        #message contenant la liste des utilisateurs
        if tipe == 0b000011 :
            self.listUser = []
            #on envoie un acquittement
            if self.numeroSequenceAttendu == num:
                Type = 0b111111
                z = ( num<<6 ) + Type 
                taille = 0b100
                message = struct.pack( '!HH' , taille , z )    
                self.transport.write(message, host_port)
                self.numeroSequenceAttendu +=1
            
            #on stocke dans une liste les couples (userName ,localisation)
            l=0
            while l != (longueur-4):

                length1 = struct.unpack('!B',data[l:1+l])[0]
                id_salon = struct.unpack('!B' , data[1+l:2+l])[0]
                print('id salon utilisateur', id_salon)
                user_name = struct.unpack(str(length1-2)+'s', data[2+l : (length1+l)])[0]
                l = l +length1
                self.listUser = self.listUser + [(user_name.decode('utf-8'), ROOM_IDS.MAIN_ROOM )]
            #affichage des listes films et utilisateurs
            self.clientProxy.initCompleteONE(self.listUser, self.listFilm)
            print('utlisation de init')
            
        

        #reception d'un message de chat
        if tipe == 0b001010:
            if self.numeroSequenceAttendu == num:
                #on envoie un acquittement
                Type = 0b111111
                z = ( num<<6 ) + Type 
                taille = 0b100
                message = struct.pack( '!HH' , taille , z )    
                self.transport.write(message, host_port)
                self.numeroSequenceAttendu +=1
            
            #on decode le message
            taille_user = struct.unpack('!B', data[:1])[0]
            nom_emetteur = struct.unpack('!' +str(taille_user)+'s', data[1:1+taille_user])[0]
            texte_message = struct.unpack('!' + str(longueur - 4 -1- taille_user) +'s', data[1+taille_user:])[0]
            chat = texte_message.decode('utf-8')
            
            print('emetteur', nom_emetteur)
            print('chat', chat)
            
            #on affiche le message si l'emetteur est différent du client
            if nom_emetteur.decode('utf-8')!= self.userName:                
                self.clientProxy.chatMessageReceivedONE(nom_emetteur.decode('utf-8'), texte_message.decode('utf-8'))

        #validation de la requete de joindre une room
        if tipe == 0b001011:
            if self.numeroSequenceAttendu == num:
                Type = 0b111111
                z = ( num<<6 ) + Type 
                taille = 0b100
                message = struct.pack( '!HH' , taille , z )    
                self.transport.write(message, host_port)
                self.numeroSequenceAttendu +=1
                print('on va rejoindre la movie room')
                self.clientProxy.joinRoomOKONE()
        

        #mise a jour de la liste des utilisateurs :
        if tipe == 0b000100:
            if self.numeroSequenceAttendu == num:
                print('nouvel utilisateur', data)
                Type = 0b111111
                z = ( num<<6 ) + Type 
                taille = 0b100
                message = struct.pack( '!HH' , taille , z )    
                self.transport.write(message, host_port)
                self.numeroSequenceAttendu +=1
            
            salle = struct.unpack('!B', data[:1])[0]
            nom = struct.unpack(str(len(data)-1)+'s', data[1:])[0]
            print('salle', salle)
            print('nom nvl utilisateur', nom)
            nom1 = self.userName.encode('utf-8')
            
            #un nouvel utilisateur vient d'arriver dans la main room
            if salle ==0 : 
                salle = ROOM_IDS.MAIN_ROOM 
            print(salle)
            
            m = (nom.decode('utf-8'), ROOM_IDS.MAIN_ROOM)
            i = m in self.listUser
           
            #le client veut quitter le systeme ou rejoindre une movie room
            if i == True and salle!=ROOM_IDS.MAIN_ROOM :
                print('utilisateur existant mise à jour loca')
                
                #quitter le système
                if salle == 255:
                    for i in self.listUser : 
                        print('liste user',i[0])
                        print('gone', nom.decode('utf-8'))
                        if i[0]== nom.decode('utf-8') :
                            self.listUser.remove(i)
                            print(self.listUser)
                            self.clientProxy.setUserListONE(self.listUser)
                #rejoindre une movie room
                else:
                    for u in self.IDFilm : 
                        if u[1]==salle:
                            self.clientProxy.userUpdateReceivedONE(nom.decode('utf-8'), u[0])
            #arrivée ou retour dans la Main Room
            elif i==True and salle == ROOM_IDS.MAIN_ROOM:
                print('retour en main room ou arrivéé en main room')
                for i in self.listUser : 
                    if i[0] == nom.decode('utf-8'):
                        self.clientProxy.userUpdateReceivedONE(nom.decode('utf-8'), ROOM_IDS.MAIN_ROOM)
                
            #nouvel utilisateur vient de se connecter
            elif i==False:
                self.listUser = self.listUser + [(nom.decode('utf-8'), ROOM_IDS.MAIN_ROOM)]
                print(self.listUser)
                self.clientProxy.setUserListONE(self.listUser)

        
        
    #########GESTION de LA FIABILITE
    
    def sendAndWait (self, buf) :
        self.etatAck = 0
        if (self.counter <= 10):
            self.counter = self.counter + 1
            self.transport.write(buf, (self.serverAddress, self.serverPort))
            print('message envoyé')
            self.timer = reactor.callLater(1, self.sendAndWait, buf)
        elif (self.counter>10):
            self.timer = None
            self.clientProxy.connectionRejectedONE("Connection disrupted")
    
    def ackRecu(self):
        if (self.timer != None):
            self.timer.cancel()
            self.counter = 0
        self.etatAck = 1
        if (self.file !=[]):
            messageSent(self.file)
            self.processEnvoi(self.file[0])
            
        self.etatAck=1
        self.seqNumAck +=1
        
    def processEnvoi(self, buf):
        if (self.file == []) or (self.etatAck ==1) :
            self.sendAndWait(buf)
        else:
            messageToSend(self.file,buf)
       
        
    
