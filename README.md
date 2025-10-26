# Blue / Green Deployment Using Nginx
This project is about deploying two services with a blue/green deployment strategy with automatic failover. This ensures that the client continues to receive response from servers even when one of the up stream servers is down.

In order to achieve this nginx server is used as a load balancer infront of two node servers. The blue is the primary server while the green is the back up. Once there is an issue with the primary server which is simulated by calling the end point /chaos/start?mode=error or /chaos/start?mode=timeout. This two end points simulates the bule server not bign available. But Tsystem is designed for automatic failover to the back up server which ensure no service disruption on the side of the client. 

To run this service locally just copy the .env.example to your .env file and the run docker compose up --build
